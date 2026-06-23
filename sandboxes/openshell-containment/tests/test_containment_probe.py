"""
T1+T4 — containment_probe: the ADLC Test-phase evaluator for the OpenShell Runtime-containment layer.

Two layers, matching the test pyramid:
  - T1 (pure classifier, no infra): the DISCRIMINATION proof / placebo-guard. The classifier is a pure
    function of a SandboxResult, so a HOLLOW/PERMISSIVE outcome (egress that SUCCEEDED, host home VISIBLE)
    is fed synthetically and MUST be flagged as a containment failure. A no-op sandbox cannot score 0 —
    this is exactly the Goodhart vector closed: count_metric=0 means real blocking, not "ran without error".
  - T4 (live, zero MagicMock): run the probe against the REAL OpenShell sandbox; assert fully contained
    (count=0). Skips (does not fail) when the gateway/sandbox is down — fail-loud is a transport RuntimeError
    surfaced as a skip reason, never a false green.

Related docs:
- Evaluator: sandboxes/openshell-containment/src/containment_probe.py
- Runner: sandboxes/openshell-containment/src/sandbox_runner.py
- Bridge: .claude/skills/mega-flow-harness-hub/harness-component/decouple-zero-trust-dr/method-problem-bridge.yaml

Migrated cc-20260611 (slice-03 of adlc-sandbox-architecture, F3): the OpenShell containment artifacts
became the `openshell-containment/` sandbox src/. Tests resolve the sandbox-local src/, not execution/scripts/.
"""
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC))

from sandbox_runner import SandboxResult  # noqa: E402
import containment_probe as cp  # noqa: E402


def _case(cid):
    return next(c for c in cp.CASES if c.cid == cid)


def _result(cmd, exit_code, stdout, stderr=""):
    return SandboxResult(cmd=cmd, exit_code=exit_code, stdout=stdout, stderr=stderr)


# ── T1: classifier discrimination (placebo-guard) ───────────────────────────

def test_egress_blocked_result_is_contained():
    """A real default-deny block (curl 56 / 403) classifies as contained."""
    case = _case("egress_exfil_blocked")
    res = _result(case.cmd, 0, "curl: (56) CONNECT tunnel failed, response 403\n[exit=56]")
    v = cp.classify(case, res)
    assert v.contained is True and v.failure is False


def test_egress_permissive_result_is_flagged():
    """PLACEBO-GUARD: if the sandbox policy were permissive, the fetch SUCCEEDS (200, body, exit 0) and
    the probe MUST flag it as a containment failure — a hollow/no-op sandbox cannot pass this case."""
    case = _case("egress_exfil_blocked")
    permissive = _result(case.cmd, 0, "<!doctype html><title>Example Domain</title>...\n[exit=0]")
    v = cp.classify(case, permissive)
    assert v.contained is False and v.failure is True


def test_fs_isolated_result_is_contained():
    case = _case("fs_host_home_isolated")
    res = _result(case.cmd, 0, "ls: cannot access '/Users': No such file or directory\n[exit=2]")
    assert cp.classify(case, res).contained is True


def test_fs_host_visible_result_is_flagged():
    """PLACEBO-GUARD: host home visible inside the sandbox = containment failure."""
    case = _case("fs_host_home_isolated")
    leaked = _result(case.cmd, 0, "neon\nShared\n[exit=0]")
    v = cp.classify(case, leaked)
    assert v.contained is False and v.failure is True


def test_legit_write_success_is_contained():
    case = _case("legit_write")
    res = _result(case.cmd, 0, cp._LEGIT_MARKER + "\n")
    assert cp.classify(case, res).contained is True


def test_legit_write_denied_is_flagged():
    """Over-restriction (legit /sandbox write denied) is ALSO a failure — containment must not break work."""
    case = _case("legit_write")
    denied = _result(case.cmd, 1, "", "sh: /sandbox/probe.txt: Permission denied")
    v = cp.classify(case, denied)
    assert v.contained is False and v.failure is True


def test_cases_cover_both_kinds():
    kinds = {c.kind for c in cp.CASES}
    assert "adversarial" in kinds and "legit" in kinds


# ── T4: live sandbox (real OpenShell, zero MagicMock) ───────────────────────

def test_live_sandbox_fully_contained():
    """Run the probe against the REAL sandbox. Skips if the gateway/sandbox is not up (transport
    RuntimeError) — never a false green. When up: every adversarial case blocked, every legit case passes."""
    try:
        verdicts = cp.run_probe(cp.DEFAULT_SANDBOX, timeout=30)
    except RuntimeError as e:
        pytest.skip(f"OpenShell gateway/sandbox not available (run openshell_gateway_bootstrap.sh up): {e}")
    failures = [v for v in verdicts if v.failure]
    assert not failures, f"containment failures (SURFACED gaps): {[(v.cid, v.evidence) for v in failures]}"
    assert len(verdicts) == len(cp.CASES)
