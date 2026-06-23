"""Unit tests for containment_rag_probe classifiers — the discrimination vector, both ways (DDR-031).

Related docs:
- Capability: sandboxes/turbovec/src/containment_rag_probe.py
- Plan: docs/plans/2026-06-18-turbovec-adlc/01-runtime-proof.md

Pure-function tests (no live sandbox): a correct workload + denied egress → contained; a degraded workload
or a SUCCEEDED egress → NOT contained. A placebo (no-op turbovec / permissive policy) cannot score 0.
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
_OC = Path(__file__).resolve().parents[2] / "openshell-containment" / "src"
sys.path.insert(0, str(_SRC))
sys.path.insert(0, str(_OC))

from containment_rag_probe import CASES, classify  # noqa: E402
from sandbox_runner import SandboxResult  # noqa: E402


def _r(exit_code: int, out: str) -> SandboxResult:
    return SandboxResult(cmd="x", exit_code=exit_code, stdout=out, stderr="")


def _case(cid: str):
    return next(c for c in CASES if c.cid == cid)


def test_rag_works_offline_perfect_recall_is_contained():
    v = classify(_case("rag_works_offline"), _r(0, "RAG_OK recall_at1=1.0 n=2000 dim=64 bit=4"))
    assert v.contained and not v.failure


def test_rag_works_offline_degraded_recall_not_contained():
    # discrimination: a placebo/broken index that doesn't self-retrieve perfectly must FAIL.
    v = classify(_case("rag_works_offline"), _r(0, "RAG_OK recall_at1=0.6 n=2000 dim=64 bit=4"))
    assert v.failure and not v.contained


def test_rag_works_offline_crash_not_contained():
    v = classify(_case("rag_works_offline"), _r(2, "RAG_FAIL ImportError no module named turbovec"))
    assert v.failure


def test_egress_denied_403_is_contained():
    v = classify(_case("rag_egress_denied"), _r(0, "curl: (56) CONNECT tunnel failed, response 403 [exit=56]"))
    assert v.contained and not v.failure


def test_egress_succeeded_not_contained():
    # discrimination: a permissive policy where egress SUCCEEDS must FAIL (count>0).
    v = classify(_case("rag_egress_denied"), _r(0, "<!doctype html><html>PyPI</html> [exit=0]"))
    assert v.failure and not v.contained
