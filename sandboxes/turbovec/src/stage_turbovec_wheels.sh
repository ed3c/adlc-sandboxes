#!/usr/bin/env bash
# stage_turbovec_wheels.sh — ONE-TIME, HOST-SIDE, USER-AUTHORIZED offline staging of turbovec into ns-sandbox.
#
# WHY offline: PyPI is default-DENIED inside the sandbox (curl (56) 403), so we cannot `pip install` from the
# net there. Path: host `pip download` (egress, one-time) → `openshell sandbox upload` → in-sandbox
# `pip install --no-index`. The sandbox python is Linux aarch64 / CPython 3.14; turbovec ships cp39-ABI3
# wheels (forward-compatible) — one wheel works. numpy needs a cp314 aarch64 wheel.
#
# Idempotent (re-run safe). FAIL-LOUD (BS #14: real exit via `echo EXIT=$?`, never `| tail` mask).
# engine-locus: a setup helper, not a gate, not auto-anything.
set -u
OS="${OPENSHELL_BIN:-$(command -v openshell || echo "$HOME/.local/bin/openshell")}"
SB="${OPENSHELL_SANDBOX_NAME:-ns-sandbox}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WHEELS="$(mktemp -d "/tmp/turbovec-wheels.XXXXXX")"
TV_VER="${TURBOVEC_VERSION:-0.8.0}"

echo "[stage] wheeldir=$WHEELS sandbox=$SB turbovec==$TV_VER"

# 1. host download — turbovec (abi3) + numpy (cp314), for the sandbox platform (linux aarch64).
python3 -m pip download "turbovec==$TV_VER" --no-deps --only-binary=:all: \
  --platform manylinux_2_28_aarch64 --python-version 3.14 --implementation cp --abi abi3 \
  -d "$WHEELS"; echo "DL_TURBOVEC_EXIT=$?"
python3 -m pip download "numpy" --only-binary=:all: \
  --platform manylinux_2_28_aarch64 --python-version 3.14 --implementation cp --abi cp314 \
  -d "$WHEELS"; echo "DL_NUMPY_EXIT=$?"
ls -1 "$WHEELS"

# 2. upload wheels + workload into the sandbox.
"$OS" sandbox exec -n "$SB" --no-tty -- sh -c 'mkdir -p /sandbox/wheels'; echo "MKDIR_EXIT=$?"
# upload signature: `openshell sandbox upload <NAME> <LOCAL_PATH> [DEST]` (NAME positional, not -n).
for w in "$WHEELS"/*.whl; do "$OS" sandbox upload "$SB" "$w" "/sandbox/wheels/$(basename "$w")"; echo "UP $(basename "$w") EXIT=$?"; done
"$OS" sandbox upload "$SB" "$HERE/turbovec_rag.py" /sandbox/turbovec_rag.py; echo "UPLOAD_RAG_EXIT=$?"

# 3. in-sandbox offline install (no egress needed).
"$OS" sandbox exec -n "$SB" --no-tty -- sh -c \
  'python3 -m pip install --no-index --find-links /sandbox/wheels turbovec numpy 2>&1; echo PIP_EXIT=$?'
echo "INSTALL_RC=$?"

# 4. verify importable (fail-loud).
"$OS" sandbox exec -n "$SB" --no-tty -- sh -c \
  'python3 -c "import turbovec,numpy;print(\"STAGED turbovec OK numpy\",numpy.__version__)" 2>&1; echo VERIFY_EXIT=$?'
echo "STAGE_DONE rc=$?"
