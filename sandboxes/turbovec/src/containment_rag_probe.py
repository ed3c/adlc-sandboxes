"""containment_rag_probe — ADLC Test-phase evaluator for the turbovec air-gapped RAG sandbox.

WHY (PG-167 meta-demand, not symptom): the turbovec DR's load-bearing claim is not "faster than FAISS"
(the primary source shows x86 2-bit is in fact slower) — it is COMPLETELY LOCAL, AIR-GAPPED RAG. This
probe turns that claim into a machine fact: it runs a real turbovec index+search INSIDE the OpenShell
ns-sandbox (default-deny egress + fs isolation) and asserts (a) it returns correct self-neighbors AND
(b) egress is denied during the workload. count_metric==0 ⟺ turbovec works with zero network ⟺ air-gapped.

COMPOSITION (Slop #2 — no new exec engine): reuses openshell-containment's sandbox_runner.run_in_sandbox.
This is the seam where the turbovec sandbox COMPOSES the containment sandbox.

ENGINE-LOCUS: report-only. A NOT-CONTAINED case is SURFACED (printed + recorded), never auto-fixed.
FAIL-LOUD: gateway down / sandbox not Ready / turbovec not staged → raise → exit 1 (UNRESOLVED), never a
silent pass (PG-126). Determinism (DDR-031): fixed case order, pure classifiers, timestamp from --iso only.

Discrimination (placebo-guard): a permissive policy would let the egress case SUCCEED → count>0; a no-op
turbovec would not print recall_at1=1.0 → count>0. count==0 is not reachable by a placebo. Classifiers are
pure functions, unit-tested both ways (tests/test_containment_rag_probe.py).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# COMPOSE openshell-containment: reuse its sandbox_runner (the single exec seam). Slop #2.
_OC_SRC = Path(__file__).resolve().parents[2] / "openshell-containment" / "src"
sys.path.insert(0, str(_OC_SRC))
from sandbox_runner import DEFAULT_SANDBOX, SandboxResult, run_in_sandbox  # noqa: E402

# Egress is BLOCKED iff curl shows: CONNECT-tunnel-refused (56), the L7 proxy 403, DNS denial, or refused.
_EGRESS_BLOCK_RE = re.compile(
    r"(?i)(\(56\)|CONNECT tunnel failed|response 403|\b403\b|policy_denied|"
    r"Could not resolve host|Connection refused|network is unreachable)"
)
# The workload is correct iff it self-retrieves perfectly (recall@1 == 1.0).
_RAG_OK_RE = re.compile(r"recall_at1=1\.0\b")

# Locate the workload inside the sandbox BY NAME (robust to openshell upload's DEST nesting: upload treats
# DEST as a directory, so the staged script may land one level deep). `-print -quit` = first match, no pipe.
_FIND_RAG = "find /sandbox -name turbovec_rag.py -type f -print -quit"


@dataclass(frozen=True)
class Case:
    cid: str
    kind: str  # "legit" | "adversarial"
    cmd: str
    contained_ok: Callable[[SandboxResult], bool]
    why: str


CASES: tuple[Case, ...] = (
    Case(
        cid="rag_works_offline",
        kind="legit",
        cmd=f'F=$({_FIND_RAG}); python3 "$F"',
        contained_ok=lambda r: r.exit_code == 0 and bool(_RAG_OK_RE.search(r.combined)),
        why="turbovec index+search must return correct self-neighbors (recall_at1=1.0) INSIDE the sandbox",
    ),
    Case(
        cid="rag_egress_denied",
        kind="adversarial",
        cmd="curl -sS --max-time 8 https://pypi.org/ 2>&1; echo [exit=$?]",
        contained_ok=lambda r: bool(_EGRESS_BLOCK_RE.search(r.combined)),
        why="default-deny egress must block network during the RAG workload (air-gapped) — pypi 403/(56)",
    ),
)


@dataclass(frozen=True)
class CaseVerdict:
    cid: str
    kind: str
    contained: bool
    failure: bool
    evidence: str


def classify(case: Case, result: SandboxResult) -> CaseVerdict:
    """Pure deterministic verdict for one case. No I/O — unit-tested against synthetic results."""
    contained = bool(case.contained_ok(result))
    return CaseVerdict(cid=case.cid, kind=case.kind, contained=contained,
                       failure=not contained, evidence=result.combined[:240])


def _precondition(sandbox: str, timeout: int) -> None:
    """Fail-loud: turbovec must be staged + importable in the sandbox (else UNRESOLVED, not a containment
    failure)."""
    r = run_in_sandbox(
        f"python3 -c 'import turbovec'; I=$?; F=$({_FIND_RAG}); "
        f"[ -n \"$F\" ] && [ $I -eq 0 ]; echo [pre_exit=$?]",
        sandbox=sandbox, timeout=timeout)
    if "[pre_exit=0]" not in r.combined:
        raise RuntimeError(
            f"turbovec not staged/importable in {sandbox} — run src/stage_turbovec_wheels.sh first. "
            f"detail: {r.combined[:200]}")


def run_probe(sandbox: str, timeout: int = 40) -> list[CaseVerdict]:
    _precondition(sandbox, timeout)
    return [classify(c, run_in_sandbox(c.cmd, sandbox=sandbox, timeout=timeout)) for c in CASES]


def _record(iso: str, sandbox: str, verdicts: list[CaseVerdict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "containment-rag-verdict/v1",
        "iso": iso,
        "sandbox": sandbox,
        "count_metric": sum(1 for v in verdicts if v.failure),
        "cases": [{"id": v.cid, "kind": v.kind, "contained": v.contained, "failure": v.failure,
                   "evidence": v.evidence} for v in verdicts],
    }
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp.replace(out_path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="turbovec air-gapped RAG containment evaluator (report-only).")
    ap.add_argument("-n", "--sandbox", default=DEFAULT_SANDBOX)
    ap.add_argument("--iso", default="")
    ap.add_argument("--timeout", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--count", action="store_true", help="print ONLY count_metric (standing-probe predicate)")
    ap.add_argument("--record", default="trace", help="dir for the verdict record")
    args = ap.parse_args(argv)

    try:
        verdicts = run_probe(args.sandbox, timeout=args.timeout)
    except RuntimeError as e:
        print(f"✗ containment_rag_probe precondition failure: {e}", file=sys.stderr)
        return 1  # UNRESOLVED, fail-loud

    count = sum(1 for v in verdicts if v.failure)
    if args.iso:
        _record(args.iso, args.sandbox, verdicts, Path(args.record) / f"{args.iso}-containment-rag-verdict.json")

    if args.count:
        print(count)
        return 0
    if args.json:
        print(json.dumps({"schema": "containment-rag-verdict/v1", "iso": args.iso, "sandbox": args.sandbox,
                          "count_metric": count,
                          "cases": [{"id": v.cid, "kind": v.kind, "contained": v.contained,
                                     "failure": v.failure, "evidence": v.evidence} for v in verdicts]},
                         ensure_ascii=False, indent=2))
        return 2 if count else 0

    print(f"# containment-rag-probe (iso={args.iso or 'n/a'}, sandbox={args.sandbox}) — REPORT-ONLY")
    print(f"  cases={len(verdicts)}  count_metric={count}  "
          f"{'✅ air-gapped RAG proven' if count == 0 else '🔴 SURFACED gap(s) — hand to human, do NOT auto-fix'}")
    for v in verdicts:
        print(f"  {'✅' if v.contained else '🔴'} [{v.kind}] {v.cid}: "
              f"{'contained' if v.contained else 'NOT CONTAINED'}")
        print(f"       evidence: {v.evidence[:140]}")
    return 2 if count else 0  # runtime tier teeth: exit 0 iff air-gapped (count==0)


if __name__ == "__main__":
    raise SystemExit(main())
