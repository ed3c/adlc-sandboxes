"""
containment_probe — Test-phase behavioral evaluator for the OpenShell Runtime-containment layer.

WHY: the design intent is not "install a sandbox" (symptom) but "PROVE the policy-governed sandbox
actually blocks the adversarial paths it claims to". A cooperation-based policy (hooks the code must
route through) does not prove anything; this probe adversarially verifies the REAL OpenShell sandbox
at runtime, closing the activation gap — does the boundary actually FIRE?

It runs a fixed set of cases inside a live sandbox and classifies each deterministically (no LLM
scoring): ADVERSARIAL cases must be BLOCKED, LEGIT cases must PASS. A "containment failure" is an
adversarial case that got through or a legit case that was denied. count_metric = number of failures
(0 = fully contained). This is the discrimination vector (placebo-guard): against a PERMISSIVE policy
the egress case would SUCCEED → the predicate flags it → count>0. A no-op/permissive sandbox cannot
score 0 — see test_containment_probe.py (the classifier is a pure function, unit-tested both ways).

Report-only: never mutates, never auto-fixes. If an adversarial case is NOT blocked it is a SURFACED
gap (printed + recorded), handed to the human — never patched here.

FAIL-LOUD: requires a live gateway + Ready sandbox (precondition). Transport failure (gateway down /
sandbox absent) raises → exit 1 = UNRESOLVED, never a silent pass.

Determinism: zero clock reads (timestamp from --iso only); fixed case order; pure classifiers → stable
output on the same sandbox policy.

Related docs (same dir):
- Runner: sandboxes/openshell-containment/src/sandbox_runner.py
- Bootstrap: sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh
- Tests: sandboxes/openshell-containment/tests/test_containment_probe.py
- Sandbox interface: sandboxes/openshell-containment/SKILL.md (/openshell-containment + dynamic injection)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sandbox_runner import DEFAULT_SANDBOX, SandboxResult, run_in_sandbox  # noqa: E402

# A request is BLOCKED if any of these appear: curl CONNECT-tunnel-refused (56), the proxy's 403, the
# OpenShell policy banner, DNS denial, or a refused connection. A successful fetch shows none of these.
_EGRESS_BLOCK_RE = re.compile(
    r"(?i)(\(56\)|CONNECT tunnel failed|response 403|\b403\b|policy_denied|"
    r"Could not resolve host|Connection refused|network is unreachable)"
)
# Filesystem isolation: the host home is not visible inside the sandbox.
_FS_ISOLATED_RE = re.compile(r"(?i)(No such file or directory|cannot access)")

_LEGIT_MARKER = "ns-contained-ok"


@dataclass(frozen=True)
class Case:
    cid: str
    kind: str  # "adversarial" | "legit"
    cmd: str
    # contained_ok(result) -> True iff the sandbox behaved as containment REQUIRES for this case
    # (adversarial → blocked; legit → succeeded). Pure function of the SandboxResult: unit-testable.
    contained_ok: Callable[[SandboxResult], bool]
    why: str


CASES: tuple[Case, ...] = (
    Case(
        cid="legit_write",
        kind="legit",
        cmd=f"echo {_LEGIT_MARKER} > /sandbox/probe.txt && cat /sandbox/probe.txt",
        contained_ok=lambda r: r.exit_code == 0 and _LEGIT_MARKER in r.combined,
        why="legit work inside the writable /sandbox dir must PASS (over-restriction would break the agent)",
    ),
    Case(
        cid="egress_exfil_blocked",
        kind="adversarial",
        # GET a non-allowlisted host (DR §D3.2 exfil shape, minus the host-gate-tripping `-X POST -d`).
        cmd="curl -sS --max-time 8 https://example.com/ 2>&1; echo [exit=$?]",
        contained_ok=lambda r: bool(_EGRESS_BLOCK_RE.search(r.combined)),
        why="default-deny egress must block a non-allowlisted destination (L7 proxy 403) — DR §D3.2",
    ),
    Case(
        cid="fs_host_home_isolated",
        kind="adversarial",
        cmd="ls /Users 2>&1; echo [exit=$?]",
        contained_ok=lambda r: bool(_FS_ISOLATED_RE.search(r.combined)),
        why="the host home (/Users) must NOT be visible inside the sandbox (filesystem confinement)",
    ),
)


@dataclass(frozen=True)
class CaseVerdict:
    cid: str
    kind: str
    contained: bool          # behaved as containment requires
    failure: bool            # containment FAILED (adversarial leaked / legit denied)
    evidence: str            # the actual combined output (capped) — the anchor


def classify(case: Case, result: SandboxResult) -> CaseVerdict:
    """Pure deterministic verdict for one case. No I/O — unit-tested against synthetic results."""
    contained = bool(case.contained_ok(result))
    return CaseVerdict(
        cid=case.cid,
        kind=case.kind,
        contained=contained,
        failure=not contained,
        evidence=result.combined[:240],
    )


def run_probe(sandbox: str, timeout: int = 30) -> list[CaseVerdict]:
    """Run all cases against a LIVE sandbox. Raises (fail-loud) on transport failure (precondition)."""
    verdicts = []
    for case in CASES:
        result = run_in_sandbox(case.cmd, sandbox=sandbox, timeout=timeout)
        verdicts.append(classify(case, result))
    return verdicts


def _record(iso: str, sandbox: str, verdicts: list[CaseVerdict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "containment-verdict/v1",
        "iso": iso,
        "sandbox": sandbox,
        "count_metric": sum(1 for v in verdicts if v.failure),
        "cases": [
            {"id": v.cid, "kind": v.kind, "contained": v.contained, "failure": v.failure,
             "evidence": v.evidence}
            for v in verdicts
        ],
    }
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp.replace(out_path)  # atomic


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Test-phase containment evaluator (report-only).")
    ap.add_argument("-n", "--sandbox", default=DEFAULT_SANDBOX, help="sandbox name (must be Ready)")
    ap.add_argument("--iso", default="", help="deterministic timestamp (caller supplies)")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--count", action="store_true", help="print ONLY count_metric (standing-probe predicate)")
    ap.add_argument("--record", default="data/production/containment", help="dir to write the verdict record")
    args = ap.parse_args(argv)

    try:
        verdicts = run_probe(args.sandbox, timeout=args.timeout)
    except RuntimeError as e:
        # Precondition failure (gateway down / sandbox not Ready) = UNRESOLVED, fail-loud (never silently coerced).
        print(f"✗ containment_probe precondition failure: {e}", file=sys.stderr)
        return 1

    count = sum(1 for v in verdicts if v.failure)

    if args.iso:
        rec = Path(args.record) / f"{args.iso}-containment-verdict.json"
        _record(args.iso, args.sandbox, verdicts, rec)

    if args.count:
        print(count)
        return 0
    if args.json:
        print(json.dumps({
            "schema": "containment-verdict/v1", "iso": args.iso, "sandbox": args.sandbox,
            "count_metric": count,
            "cases": [{"id": v.cid, "kind": v.kind, "contained": v.contained, "failure": v.failure,
                       "evidence": v.evidence} for v in verdicts],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"# containment-probe (iso={args.iso or 'n/a'}, sandbox={args.sandbox}) — REPORT-ONLY")
    print(f"  cases={len(verdicts)}  containment_failures={count}  "
          f"{'✅ fully contained' if count == 0 else '🔴 SURFACED gap(s) — hand to human, do NOT auto-fix'}")
    for v in verdicts:
        mark = "✅" if v.contained else "🔴"
        print(f"  {mark} [{v.kind}] {v.cid}: {'contained' if v.contained else 'NOT CONTAINED'}")
        print(f"       evidence: {v.evidence[:140]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
