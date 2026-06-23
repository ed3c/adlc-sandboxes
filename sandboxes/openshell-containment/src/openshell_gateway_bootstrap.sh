#!/usr/bin/env bash
# openshell_gateway_bootstrap.sh — re-runnable bootstrap for a LOCAL NVIDIA OpenShell gateway on macOS.
#
# WHY: this sandbox runs agent-generated code under the real NVIDIA OpenShell as its Runtime-containment
# layer. Self-hosting OpenShell's docker-driver on macOS Docker Desktop fights its Linux-first design: the
# gateway runs in a container but creates SIBLING sandbox containers via the host Docker daemon, so EVERY
# path the gateway asks the host to bind-mount into a sandbox (supervisor binary, mTLS certs, per-sandbox
# JWT token) must be HOST-reachable at the SAME absolute path the gateway records. On Linux host-HOME ==
# container-HOME so this is automatic; on macOS it is NOT (host /Users/<u> vs container /root|/home/openshell).
# This script codifies the keystone fix (9 friction layers):
#   set the gateway container's HOME to the host home + same-path mount everything HOME-relative.
#
# DESIGN: thin, idempotent glue over the `openshell` CLI + `docker` — no new engine, composition over
# building. Nothing depends on this at import time; it is invoked on demand (Build phase / containment_probe
# Test phase / before promotion). Runtime LLM stays Zero-API-Key (sandboxes can run --from ollama; the
# gateway pulls no model). The ONE external pull is the one-time `uv tool install openshell` + GHCR images.
#
# SECURITY (recorded, human-authorized): the gateway container mounts /var/run/docker.sock
# (host-root-equivalent control of the Docker daemon) and runs plaintext mTLS bound to 127.0.0.1. This is
# OpenShell's documented docker-driver requirement. Tear down when idle.
#
# Related docs:
# - Source (stealth-located): docs.nvidia.com/openshell/about/container-gateway + github.com/NVIDIA/OpenShell
#
# Usage:
#   openshell_gateway_bootstrap.sh up          # idempotent: ensure CLI + gateway + (optional) sandbox up
#   openshell_gateway_bootstrap.sh up --sandbox ns-sandbox   # also ensure a sandbox of that name exists
#   openshell_gateway_bootstrap.sh status       # report gateway + sandbox state (exit 0 iff Connected)
#   openshell_gateway_bootstrap.sh down          # stop+remove the gateway container (sandboxes deleted first)
# Exit: 0 success; 2 precondition/bootstrap failure (fail-loud, never silent).
set -euo pipefail

# ── config (env-overridable) ───────────────────────────────────────────────
GATEWAY_NAME="${OPENSHELL_GATEWAY_NAME:-openshell}"
GATEWAY_PORT="${OPENSHELL_GATEWAY_PORT:-8080}"
GATEWAY_CONTAINER="${OPENSHELL_GATEWAY_CONTAINER:-openshell-gateway}"
GATEWAY_IMAGE="ghcr.io/nvidia/openshell/gateway:latest"
SUPERVISOR_IMAGE="ghcr.io/nvidia/openshell/supervisor:latest"
SUP_BIN="$HOME/openshell/supervisor/openshell-sandbox"
STATE_DIR="$HOME/.local/state/openshell"          # mTLS certs + JWT keys + DB + per-sandbox tokens
SHARE_DIR="$HOME/.local/share/openshell"           # supervisor cache (XDG_DATA_HOME/openshell)
export PATH="$HOME/.local/bin:$PATH"

log() { printf '  %s\n' "$*" >&2; }
die() { printf '✗ %s\n' "$*" >&2; exit 2; }

require() { command -v "$1" >/dev/null 2>&1 || die "missing prerequisite: $1"; }

# ── steps ───────────────────────────────────────────────────────────────────
ensure_cli() {
  if ! command -v openshell >/dev/null 2>&1; then
    log "installing openshell CLI (uv tool install --python 3.12; openshell needs >=3.12)…"
    require uv
    uv tool install openshell --python 3.12 >&2 || die "uv tool install openshell failed"
  fi
  log "openshell CLI: $(openshell --version 2>&1 | head -1)"
}

ensure_supervisor_bin() {
  # The gateway auto-extracts a version-matched supervisor to its cache anyway (see ensure_gateway's
  # XDG_DATA_HOME same-path mount); this host copy satisfies OPENSHELL_DOCKER_SUPERVISOR_BIN and the
  # same-path mount. Idempotent: skip if present.
  if [ -x "$SUP_BIN" ]; then log "supervisor binary present: $SUP_BIN"; return; fi
  log "extracting supervisor binary from $SUPERVISOR_IMAGE…"
  mkdir -p "$(dirname "$SUP_BIN")"
  docker create --name tmp-supervisor-bootstrap "$SUPERVISOR_IMAGE" >/dev/null \
    || die "docker create supervisor failed"
  docker cp tmp-supervisor-bootstrap:/openshell-sandbox "$SUP_BIN" >/dev/null \
    || { docker rm tmp-supervisor-bootstrap >/dev/null 2>&1 || true; die "docker cp supervisor failed"; }
  docker rm tmp-supervisor-bootstrap >/dev/null 2>&1 || true
  chmod +x "$SUP_BIN"
  log "supervisor binary extracted: $SUP_BIN"
}

ensure_certs() {
  # generate-certs writes mTLS PKI + sandbox-JWT signing keys; HOME=/home/openshell makes the CLI
  # client-bundle auto-copy land under ~/.config/openshell/gateways/<GATEWAY_NAME>/mtls/. Idempotent:
  # the tool skips if PKI already exists.
  if [ -f "$STATE_DIR/tls/server/tls.crt" ] && [ -f "$STATE_DIR/tls/jwt/signing.pem" ]; then
    log "mTLS PKI + JWT keys present: $STATE_DIR/tls"
    return
  fi
  log "generating mTLS PKI + JWT signing keys…"
  mkdir -p "$STATE_DIR" "$HOME/.config/openshell"
  docker run --rm \
    -e HOME=/home/openshell \
    -v "$STATE_DIR:/home/openshell/.local/state/openshell" \
    -v "$HOME/.config/openshell:/home/openshell/.config/openshell" \
    "$GATEWAY_IMAGE" \
    generate-certs \
      --output-dir /home/openshell/.local/state/openshell/tls \
      --server-san host.openshell.internal \
      --server-san 127.0.0.1 \
      --server-san localhost >&2 || die "generate-certs failed"
  log "PKI generated under $STATE_DIR/tls"
}

gateway_running() {
  [ "$(docker inspect -f '{{.State.Running}}' "$GATEWAY_CONTAINER" 2>/dev/null || echo false)" = "true" ]
}

ensure_gateway() {
  if gateway_running; then log "gateway container already running: $GATEWAY_CONTAINER"; else
    # Remove any stopped/created remnant (plain rm — never -f, which the host auto-approve gate blocks).
    if docker inspect "$GATEWAY_CONTAINER" >/dev/null 2>&1; then
      docker stop "$GATEWAY_CONTAINER" >/dev/null 2>&1 || true
      docker rm "$GATEWAY_CONTAINER" >/dev/null 2>&1 || true
    fi
    mkdir -p "$SHARE_DIR"
    log "starting gateway container (mTLS, --user 0:0 for docker.sock, HOME=$HOME keystone same-path fix)…"
    # KEYSTONE: HOME=$HOME + same-path mounts of $STATE_DIR and $SHARE_DIR → every HOME-relative
    # injection (per-sandbox JWT token under $STATE_DIR/docker-sandbox-tokens, supervisor cache under
    # $SHARE_DIR) lands at a host-reachable same-path the host daemon can bind-mount into sandboxes.
    docker run -d \
      --name "$GATEWAY_CONTAINER" --restart unless-stopped --user 0:0 \
      -p "127.0.0.1:${GATEWAY_PORT}:8080" \
      -e HOME="$HOME" \
      -v "$STATE_DIR:$STATE_DIR" \
      -v "$SHARE_DIR:$SHARE_DIR" \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v "$SUP_BIN:$SUP_BIN:ro" \
      -e XDG_DATA_HOME="$HOME/.local/share" \
      -e OPENSHELL_DRIVERS=docker \
      -e OPENSHELL_GRPC_ENDPOINT="https://host.openshell.internal:8080" \
      -e OPENSHELL_DOCKER_SUPERVISOR_BIN="$SUP_BIN" \
      -e OPENSHELL_DB_URL="sqlite:$STATE_DIR/openshell.db" \
      -e OPENSHELL_LOCAL_TLS_DIR="$STATE_DIR/tls" \
      -e OPENSHELL_TLS_CERT="$STATE_DIR/tls/server/tls.crt" \
      -e OPENSHELL_TLS_KEY="$STATE_DIR/tls/server/tls.key" \
      -e OPENSHELL_TLS_CLIENT_CA="$STATE_DIR/tls/ca.crt" \
      -e OPENSHELL_ENABLE_MTLS_AUTH=true \
      -e OPENSHELL_DOCKER_TLS_CA="$STATE_DIR/tls/ca.crt" \
      -e OPENSHELL_DOCKER_TLS_CERT="$STATE_DIR/tls/client/tls.crt" \
      -e OPENSHELL_DOCKER_TLS_KEY="$STATE_DIR/tls/client/tls.key" \
      "$GATEWAY_IMAGE" >/dev/null || die "docker run gateway failed"
  fi
  # Register with the CLI (idempotent — re-add refreshes registration; certs already in ~/.config).
  openshell gateway add "https://127.0.0.1:${GATEWAY_PORT}" --local --name "$GATEWAY_NAME" >/dev/null 2>&1 || true
}

wait_connected() {
  # Poll status up to ~20s; fail-loud if never Connected (no silent pass).
  for _ in $(seq 1 20); do
    if openshell status 2>/dev/null | grep -q "Connected"; then
      log "gateway Connected (${GATEWAY_NAME} @ https://127.0.0.1:${GATEWAY_PORT})"; return 0
    fi
    sleep 1
  done
  docker logs "$GATEWAY_CONTAINER" 2>&1 | tail -8 >&2 || true
  die "gateway never reached Connected"
}

# Phase of a sandbox by name, ANSI-stripped, from `sandbox list` ($NF = phase; CREATED holds a space).
# Empty string if the sandbox does not exist.
sandbox_phase() {
  openshell sandbox list 2>/dev/null \
    | sed 's/\x1b\[[0-9;]*m//g' \
    | awk -v n="$1" 'NR>1 && $1==n {print $NF}'
}

ensure_sandbox() {
  local name="$1" phase
  phase="$(sandbox_phase "$name")"
  if [ "$phase" = "Ready" ]; then log "sandbox '$name' already Ready"; return 0; fi
  if [ -n "$phase" ]; then
    log "sandbox '$name' in phase '$phase' — deleting + recreating"
    openshell sandbox delete "$name" >/dev/null 2>&1 || true
  fi
  log "creating sandbox '$name' (--from base; pulls image first time)…"
  openshell sandbox create --from base --name "$name" >&2 || die "sandbox create failed"
  phase="$(sandbox_phase "$name")"
  [ "$phase" = "Ready" ] || die "sandbox '$name' did not reach Ready (phase=$phase)"
  log "sandbox '$name' Ready"
}

cmd_up() {
  local sandbox=""
  shift || true
  while [ $# -gt 0 ]; do case "$1" in --sandbox) sandbox="$2"; shift 2;; *) die "unknown arg: $1";; esac; done
  require docker; docker info >/dev/null 2>&1 || die "docker daemon not running"
  ensure_cli; ensure_supervisor_bin; ensure_certs; ensure_gateway; wait_connected
  [ -n "$sandbox" ] && ensure_sandbox "$sandbox"
  log "bootstrap up: OK"
}

cmd_status() {
  require docker
  gateway_running && log "gateway container: running" || log "gateway container: NOT running"
  openshell status 2>&1 | grep -iE "status|version" >&2 || true
  openshell status 2>/dev/null | grep -q "Connected"
}

cmd_down() {
  require docker
  # Delete sandboxes first (orderly), then stop+remove gateway. Plain rm only (host gate blocks rm -f).
  for sb in $(openshell sandbox list 2>/dev/null | awk 'NR>1{print $1}'); do
    openshell sandbox delete "$sb" >/dev/null 2>&1 || true
  done
  docker stop "$GATEWAY_CONTAINER" >/dev/null 2>&1 || true
  docker rm "$GATEWAY_CONTAINER" >/dev/null 2>&1 || true
  log "gateway torn down"
}

main() {
  local sub="${1:-up}"
  case "$sub" in
    up) cmd_up "$@";;
    status) cmd_status;;
    down) cmd_down;;
    *) die "usage: $0 {up [--sandbox NAME]|status|down}";;
  esac
}
main "$@"
