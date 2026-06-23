"""
sandbox_runner — thin abstraction over `openshell sandbox exec` to run agent-generated code inside
the NVIDIA OpenShell Runtime-containment layer (ADLC "develop a sandbox", bridge decouple-zero-trust-dr).

WHY a thin wrapper (not a new engine, Slop #2): northstar's "agent" = skill + hook + dispatch
composition. When such a composition needs to EXECUTE untrusted/agent-generated code, this is the
single seam that routes it through the policy-governed sandbox instead of the host. It shells to the
`openshell` CLI deliberately — OpenShell is alpha (v0.0.59), so northstar stays loosely coupled behind
this one function and could swap the primitive (e.g. sandbox-exec) without touching callers.

This module is the Build-phase deliverable; containment_probe.py (Test phase) is its first consumer.
NOT a gate, NOT auto-anything — a library function + a tiny CLI for manual use.

Determinism / fail-loud: a missing CLI or an unreachable gateway raises (never silently "succeeds").
The returned SandboxResult carries the REAL remote exit code (the CLI exits with the remote command's
exit code), stdout, stderr — callers classify; this layer does not interpret.

Related docs (migrated cc-20260611 into the openshell-containment sandbox, slice-03 F3):
- ADLC module: .claude/skills/mega-flow-harness-hub/modules/adlc-lifecycle.md (Runtime layer)
- Bootstrap: sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh (same dir)
- Consumer: sandboxes/openshell-containment/src/containment_probe.py (same dir)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

DEFAULT_SANDBOX = os.environ.get("OPENSHELL_SANDBOX_NAME", "ns-sandbox")
# uv tool installs land in ~/.local/bin which may be off a non-login PATH; resolve robustly.
_OPENSHELL_CANDIDATES = ("openshell", os.path.expanduser("~/.local/bin/openshell"))


def _openshell_bin() -> str:
    for cand in _OPENSHELL_CANDIDATES:
        resolved = shutil.which(cand) or (cand if os.path.exists(cand) else None)
        if resolved:
            return resolved
    raise RuntimeError(
        "openshell CLI not found (tried: %s). Run execution/scripts/openshell_gateway_bootstrap.sh up"
        % ", ".join(_OPENSHELL_CANDIDATES)
    )


@dataclass(frozen=True)
class SandboxResult:
    """Raw outcome of one in-sandbox command. exit_code is the REMOTE command's code (CLI propagates it)."""
    cmd: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def combined(self) -> str:
        return (self.stdout + "\n" + self.stderr).strip()


def run_in_sandbox(cmd: str, sandbox: str = DEFAULT_SANDBOX, timeout: int = 30) -> SandboxResult:
    """Run `cmd` (a shell string) inside `sandbox` via `openshell sandbox exec`. Fail-loud on infra error.

    Raises RuntimeError if the CLI is missing or the exec transport itself fails (gateway down / sandbox
    not Ready) — distinct from the remote command merely exiting non-zero (which is a normal result).
    """
    bin_ = _openshell_bin()
    argv = [bin_, "sandbox", "exec", "-n", sandbox, "--no-tty", "--", "sh", "-c", cmd]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"sandbox exec timed out after {timeout}s: {cmd}") from e
    # The CLI prints its own transport errors (e.g. "sandbox not Ready", "no active gateway") to stderr
    # AND exits non-zero with no remote stdout. Distinguish transport failure from a genuine remote
    # non-zero: transport failures carry a recognizable CLI banner and empty remote output.
    transport_markers = ("no active gateway", "not in Ready", "not found", "FailedPrecondition",
                         "connection refused", "Error: ")
    if proc.returncode != 0 and not proc.stdout and any(m in proc.stderr for m in transport_markers):
        raise RuntimeError(f"sandbox exec transport failure (gateway/sandbox not usable): {proc.stderr.strip()}")
    return SandboxResult(cmd=cmd, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a command inside the OpenShell sandbox (thin wrapper).")
    ap.add_argument("command", help="shell command to run inside the sandbox")
    ap.add_argument("-n", "--sandbox", default=DEFAULT_SANDBOX, help="sandbox name")
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args(argv)
    try:
        res = run_in_sandbox(args.command, sandbox=args.sandbox, timeout=args.timeout)
    except RuntimeError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    if res.stdout:
        sys.stdout.write(res.stdout)
    if res.stderr:
        sys.stderr.write(res.stderr)
    return res.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
