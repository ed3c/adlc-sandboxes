"""
loop_kernel behavior tests — full-branch coverage of the deterministic DECIDE gate.

The kernel is a PURE function of (rubric, scorecard): no Ollama, no network, no datetime.now().
These test BEHAVIOR through the public interface (decide / validate_scorecard / load_rubric /
advance), not implementation detail. Every DECIDE branch, every fail-loud input defect, and every
bounded-loop guard (no-progress plateau / exhaustion) is exercised.

Related docs:
- Implementation: sandboxes/self-correcting-loop/src/loop_kernel.py
- Interface contract: sandboxes/self-correcting-loop/SKILL.md (C1-C5)
- Loop governance: .claude/skills/adlc/skill.md S1/S3
"""
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC))

import loop_kernel as lk  # noqa: E402


def _rubric(*ids_thresholds):
    """Build a rubric from (id, threshold) pairs in declared order."""
    return lk.load_rubric([{"id": i, "threshold": t} for i, t in ids_thresholds])


# ── decide: FINAL / ITERATING ────────────────────────────────────────────────

def test_final_when_every_criterion_meets_threshold():
    r = _rubric(("a", 8), ("b", 8))
    d = lk.decide(r, {"a": 8, "b": 9})
    assert d.verdict == "FINAL"
    assert d.focus is None
    assert d.failing == []
    assert d.min_score == 8


def test_iterating_focus_is_the_single_failing_criterion():
    r = _rubric(("a", 8), ("b", 8))
    d = lk.decide(r, {"a": 9, "b": 5})
    assert d.verdict == "ITERATING"
    assert d.focus == "b"
    assert d.failing == ["b"]
    assert d.min_score == 5


def test_focus_is_lowest_scoring_failing_criterion():
    r = _rubric(("a", 8), ("b", 8), ("c", 8))
    d = lk.decide(r, {"a": 7, "b": 3, "c": 6})
    assert d.focus == "b"                       # lowest score wins
    assert d.failing == ["b", "c", "a"]         # weakest-first


def test_focus_tie_breaks_on_rubric_declared_order():
    r = _rubric(("first", 8), ("second", 8))
    d = lk.decide(r, {"first": 4, "second": 4})  # equal scores
    assert d.focus == "first"                    # declared order breaks the tie (deterministic)


def test_per_criterion_records_pass_flags():
    r = _rubric(("a", 8), ("b", 6))
    d = lk.decide(r, {"a": 7, "b": 6})
    # rubric criteria carry kind="rubric" (the additive D3 field); scores/thresholds/pass unchanged
    assert d.per_criterion["a"] == {"score": 7, "threshold": 8, "pass": False, "kind": "rubric"}
    assert d.per_criterion["b"] == {"score": 6, "threshold": 6, "pass": True, "kind": "rubric"}


def test_decide_is_pure_same_inputs_same_decision():
    r = _rubric(("a", 8), ("b", 8))
    sc = {"a": 4, "b": 9}
    assert lk.decide(r, sc).to_dict() == lk.decide(r, sc).to_dict()


# ── validate_scorecard: fail-loud input defects ──────────────────────────────

def test_missing_score_fails_loud():
    r = _rubric(("a", 8), ("b", 8))
    with pytest.raises(lk.RubricError, match="missing"):
        lk.validate_scorecard(r, {"a": 8})


def test_unknown_criterion_fails_loud():
    r = _rubric(("a", 8))
    with pytest.raises(lk.RubricError, match="unknown"):
        lk.validate_scorecard(r, {"a": 8, "ghost": 9})


@pytest.mark.parametrize("bad", [0, 11, -1, 99])
def test_out_of_range_score_fails_loud(bad):
    r = _rubric(("a", 8))
    with pytest.raises(lk.RubricError):
        lk.validate_scorecard(r, {"a": bad})


def test_bool_score_rejected_not_coerced_to_int():
    r = _rubric(("a", 8))
    with pytest.raises(lk.RubricError):
        lk.validate_scorecard(r, {"a": True})   # True == 1 in python — must NOT be accepted


def test_non_dict_scorecard_fails_loud():
    r = _rubric(("a", 8))
    with pytest.raises(lk.RubricError):
        lk.validate_scorecard(r, ["a", 8])


# ── load_rubric: fail-loud structure defects ─────────────────────────────────

def test_empty_rubric_fails_loud():
    with pytest.raises(lk.RubricError):
        lk.load_rubric([])


def test_duplicate_criterion_id_fails_loud():
    with pytest.raises(lk.RubricError, match="duplicate"):
        lk.load_rubric([{"id": "a"}, {"id": "a"}])


def test_bad_threshold_fails_loud():
    with pytest.raises(lk.RubricError, match="threshold"):
        lk.load_rubric([{"id": "a", "threshold": 99}])


def test_dict_form_with_criteria_key_accepted():
    r = lk.load_rubric({"criteria": [{"id": "a"}]})
    assert [c.id for c in r] == ["a"]
    assert r[0].threshold == lk.DEFAULT_THRESHOLD   # default applied


# ── advance: bounded-loop state tracking ─────────────────────────────────────

def _record(state, scorecard, iso="2026-06-23"):
    r = _rubric(("a", 8))
    return lk.advance(state, iso, scorecard, lk.decide(r, scorecard))


def test_advance_appends_and_numbers_iterations():
    state: dict = {}
    _record(state, {"a": 4})
    _record(state, {"a": 6})
    assert [it["iteration"] for it in state["iterations"]] == [1, 2]
    assert state["verdict"] == "ITERATING"


def test_advance_final_clears_guards():
    state: dict = {}
    _record(state, {"a": 9})
    assert state["verdict"] == "FINAL"
    assert state["no_progress"] is False
    assert state["exhausted"] is False


def test_no_progress_detected_on_plateau():
    state = {"no_progress_window": 3}
    for _ in range(3):
        _record(state, {"a": 5})                 # flat min_score, never improving, never FINAL
    assert state["no_progress"] is True


def test_no_progress_false_when_improving():
    state = {"no_progress_window": 3}
    for s in (3, 5, 7):                           # strictly improving
        _record(state, {"a": s})
    assert state["no_progress"] is False


def test_exhausted_when_max_iterations_reached_without_final():
    state = {"max_iterations": 2}
    _record(state, {"a": 4})
    assert state["exhausted"] is False
    _record(state, {"a": 4})
    assert state["exhausted"] is True


def test_detect_no_progress_false_below_window():
    assert lk._detect_no_progress([{"min_score": 5}], window=3) is False


# ── runnable criteria (D3: pass/fail = command EXIT CODE, not an LLM rubric score) ─────
# A `kind: runnable` criterion's scorecard value is a real command exit code (VERIFY runs the
# command). Kernel: runnable-pass = (exit_code == 0). Orthogonal to rubric criteria; both kinds
# coexist in ONE decide(). effective_score unifies ordering: runnable → SCORE_MAX if pass else 0.

def _mixed_rubric(*specs):
    """Build a mixed rubric from (id, kind, threshold) triples; threshold ignored for runnable."""
    out = []
    for cid, kind, thr in specs:
        c = {"id": cid, "kind": kind}
        if kind == "rubric":
            c["threshold"] = thr
        out.append(c)
    return lk.load_rubric(out)


def test_runnable_criterion_passes_on_exit_zero():
    r = _mixed_rubric(("tests", "runnable", None))
    d = lk.decide(r, {"tests": 0})
    assert d.verdict == "FINAL"
    assert d.focus is None
    assert d.per_criterion["tests"]["pass"] is True
    assert d.per_criterion["tests"]["kind"] == "runnable"
    assert d.per_criterion["tests"]["threshold"] == "runnable"   # threshold irrelevant for runnable


def test_runnable_plus_rubric_final_iff_all_pass():
    r = _mixed_rubric(("tests", "runnable", None), ("readability", "rubric", 8))
    assert lk.decide(r, {"tests": 0, "readability": 8}).verdict == "FINAL"
    # runnable still green but rubric below threshold → not FINAL
    assert lk.decide(r, {"tests": 0, "readability": 5}).verdict == "ITERATING"


# REVERSE-MUTANT GUARD: a kernel that ignores the exit code (always-passes runnable) would
# mark this FINAL with focus=None. The exit-1 → ITERATING + focus==runnable assertion is the
# discriminator that catches such a mutant.
def test_runnable_criterion_fails_on_nonzero_exit():
    r = _mixed_rubric(("tests", "runnable", None))
    d = lk.decide(r, {"tests": 1})
    assert d.verdict == "ITERATING"          # ← reverse-mutant discriminator
    assert d.focus == "tests"
    assert d.failing == ["tests"]
    assert d.per_criterion["tests"]["pass"] is False
    assert d.min_score == 0                  # failing runnable pins min_score at 0 (no-progress source)


def test_failing_runnable_focuses_before_low_rubric_score():
    # mixed: a failing test (hard blocker, effective 0) must focus BEFORE a low rubric score (3)
    r = _mixed_rubric(("tests", "runnable", None), ("readability", "rubric", 8))
    d = lk.decide(r, {"tests": 1, "readability": 3})
    assert d.verdict == "ITERATING"
    assert d.focus == "tests"                # effective 0 < effective 3 → runnable focuses first
    assert d.failing == ["tests", "readability"]


def test_passing_runnable_effective_score_does_not_pin_min():
    # a passing runnable contributes SCORE_MAX to effective ordering, so min_score reflects the rubric
    r = _mixed_rubric(("tests", "runnable", None), ("readability", "rubric", 8))
    d = lk.decide(r, {"tests": 0, "readability": 6})
    assert d.min_score == 6                  # passing runnable (effective 10) does not drag min below rubric


def test_runnable_higher_exit_code_still_just_fails():
    r = _mixed_rubric(("tests", "runnable", None))
    d = lk.decide(r, {"tests": 137})         # any non-zero exit = fail (exit code value is not a score)
    assert d.verdict == "ITERATING"
    assert d.focus == "tests"


# ── runnable fail-loud: exit code must be a non-negative int, never a rubric-style 1-10 ─────

def test_runnable_negative_exit_fails_loud():
    r = _mixed_rubric(("tests", "runnable", None))
    with pytest.raises(lk.RubricError):
        lk.validate_scorecard(r, {"tests": -1})


def test_runnable_bool_exit_fails_loud():
    r = _mixed_rubric(("tests", "runnable", None))
    with pytest.raises(lk.RubricError):
        lk.validate_scorecard(r, {"tests": True})   # True == 1 in python — must NOT be accepted


def test_runnable_non_int_exit_fails_loud():
    r = _mixed_rubric(("tests", "runnable", None))
    with pytest.raises(lk.RubricError):
        lk.validate_scorecard(r, {"tests": "x"})


def test_runnable_large_exit_code_accepted():
    r = _mixed_rubric(("tests", "runnable", None))
    lk.validate_scorecard(r, {"tests": 255})         # any non-negative int is a legal exit code


def test_unknown_kind_fails_loud():
    with pytest.raises(lk.RubricError, match="kind"):
        lk.load_rubric([{"id": "a", "kind": "magic"}])


def test_kind_defaults_to_rubric_back_compat():
    r = lk.load_rubric([{"id": "a", "threshold": 8}])   # no kind key
    assert r[0].kind == "rubric"


# ── CLI selftest = the runtime_trace_cmd the absorb gate runs ────────────────

def test_selftest_exits_zero(tmp_path, capsys):
    # selftest writes a trace under ../trace; run it and assert green exit
    rc = lk._main(["loop_kernel", "selftest", "--iso", "2026-06-23T00:00:00Z"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "🟢" in out
    assert "FAIL" not in out
