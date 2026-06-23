#!/usr/bin/env python3
"""loop_kernel — deterministic DECIDE gate for a PLAN/DO/VERIFY/DECIDE self-correcting loop.

WHY: a self-correcting refinement loop ("iterate until every rubric criterion >= threshold") is
only as honest as its DECIDE step. If an LLM both produces the artifact AND judges "all criteria
are 8/10, so FINAL", the loop can self-deceive (hallucination propagation; structure passes but
behavior fails). This kernel MECHANIZES the DECIDE step into a determinate function (deterministic,
zero LLM scoring): FINAL is entailed by actual scores >= thresholds, never by an agent's prose
claim. The LLM still owns PLAN (what to fix), DO (produce/improve), and VERIFY (assign each
criterion a score); the kernel owns only DECIDE + convergence tracking + the bounded-iteration
SURFACE guard.

This COMPOSES the existing loop layer rather than building a new engine: autoresearch is the
code-metric iteration instance, /refactor-loop the refactor instance; this is the generic
artifact-to-rubric instance whose one novel part is the deterministic DECIDE gate.

DETERMINISM: pure functions; no datetime.now()/random — the only timestamp source is an explicit
`iso` argument. Tie-breaking is fully ordered (lowest score, then rubric declared order), so
decide() is a pure function of inputs.

EXIT SEMANTICS (CLI):
  selftest : 0 = kernel behaves correctly against bundled fixtures · 1 = a self-check failed
  decide   : 0 = FINAL · 3 = ITERATING (distinct non-error code so a driver can branch) · 1 = bad input
  state    : 0 = printed a bounded loop-state snapshot · 1 = no such loop / unreadable

Related docs:
- Interface contract: sandboxes/self-correcting-loop/SKILL.md (C1-C5) + manifest.yaml
- Convention: sandboxes/README.md + sandboxes/_TEMPLATE/
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCORE_MIN, SCORE_MAX = 1, 10
DEFAULT_THRESHOLD = 8
DEFAULT_MAX_ITERATIONS = 10        # bounded loop (autoresearch Iterations guard) — never infinite
DEFAULT_NO_PROGRESS_WINDOW = 3     # consecutive non-improving iterations => SURFACE to human

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


class RubricError(Exception):
    """Fail-loud input defect (malformed rubric / scorecard). Never silently coerced."""


@dataclass(frozen=True)
class Criterion:
    id: str
    threshold: int = DEFAULT_THRESHOLD
    description: str = ""


@dataclass
class Decision:
    verdict: str                       # "FINAL" | "ITERATING"
    focus: str | None                  # weakest failing criterion id; None iff FINAL
    min_score: int
    failing: list[str]                 # criteria below threshold, weakest-first
    per_criterion: dict                # id -> {"score","threshold","pass"}

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict, "focus": self.focus, "min_score": self.min_score,
            "failing": self.failing, "per_criterion": self.per_criterion,
        }


# ── parsing / validation (fail-loud) ──────────────────────────────────────────

def load_rubric(obj) -> list[Criterion]:
    """Accept a list of criterion dicts or {"criteria": [...]}. Fail-loud on empty / dup / bad threshold."""
    if isinstance(obj, dict):
        obj = obj.get("criteria")
    if not isinstance(obj, list) or not obj:
        raise RubricError("rubric must be a non-empty list of criteria (or {'criteria': [...]})")
    out: list[Criterion] = []
    seen: set[str] = set()
    for i, c in enumerate(obj):
        if not isinstance(c, dict) or "id" not in c:
            raise RubricError(f"criterion #{i} must be a dict with an 'id'")
        cid = str(c["id"])
        if cid in seen:
            raise RubricError(f"duplicate criterion id {cid!r}")
        seen.add(cid)
        thr = c.get("threshold", DEFAULT_THRESHOLD)
        if not isinstance(thr, int) or not (SCORE_MIN <= thr <= SCORE_MAX):
            raise RubricError(f"criterion {cid!r} threshold must be an int in [{SCORE_MIN},{SCORE_MAX}], got {thr!r}")
        out.append(Criterion(id=cid, threshold=thr, description=str(c.get("description", ""))))
    return out


def validate_scorecard(rubric: list[Criterion], scorecard: dict) -> None:
    """Every rubric criterion must be scored, in range. Extra/missing keys fail loud (no silent default)."""
    if not isinstance(scorecard, dict):
        raise RubricError("scorecard must be a dict of {criterion_id: score}")
    rubric_ids = {c.id for c in rubric}
    missing = sorted(rubric_ids - scorecard.keys())
    if missing:
        raise RubricError(f"scorecard missing scores for: {missing}")
    extra = sorted(scorecard.keys() - rubric_ids)
    if extra:
        raise RubricError(f"scorecard has unknown criteria not in rubric: {extra}")
    for cid in sorted(rubric_ids):
        s = scorecard[cid]
        if not isinstance(s, int) or isinstance(s, bool) or not (SCORE_MIN <= s <= SCORE_MAX):
            raise RubricError(f"score for {cid!r} must be an int in [{SCORE_MIN},{SCORE_MAX}], got {s!r}")


# ── the deterministic DECIDE gate ─────────────────────────────────────────────

def decide(rubric: list[Criterion], scorecard: dict) -> Decision:
    """Pure: FINAL iff every criterion score >= its threshold; else ITERATING with the weakest
    failing criterion as focus. Tie-break = lowest score, then rubric declared order (stable)."""
    validate_scorecard(rubric, scorecard)
    order = {c.id: i for i, c in enumerate(rubric)}
    per: dict = {}
    failing: list[str] = []
    for c in rubric:
        s = scorecard[c.id]
        passed = s >= c.threshold
        per[c.id] = {"score": s, "threshold": c.threshold, "pass": passed}
        if not passed:
            failing.append(c.id)
    failing.sort(key=lambda cid: (scorecard[cid], order[cid]))
    verdict = "FINAL" if not failing else "ITERATING"
    focus = failing[0] if failing else None
    min_score = min(scorecard[c.id] for c in rubric)
    return Decision(verdict=verdict, focus=focus, min_score=min_score, failing=failing, per_criterion=per)


# ── bounded loop-state tracking (anti-infinite-loop SURFACE guard) ─────────────

def _detect_no_progress(iterations: list[dict], window: int) -> bool:
    """True iff the last `window` iterations show no min_score improvement (a plateau worth SURFACing)."""
    if len(iterations) < window:
        return False
    tail = iterations[-window:]
    return max(it["min_score"] for it in tail) <= tail[0]["min_score"]


def advance(state: dict, iso: str, scorecard: dict, decision: Decision) -> dict:
    """Append this iteration to loop-state and recompute the bounded-loop guards. Caller persists."""
    state.setdefault("iterations", [])
    state.setdefault("max_iterations", DEFAULT_MAX_ITERATIONS)
    window = state.setdefault("no_progress_window", DEFAULT_NO_PROGRESS_WINDOW)
    state["iterations"].append({
        "iteration": len(state["iterations"]) + 1, "iso": iso, "scorecard": dict(scorecard),
        "verdict": decision.verdict, "focus": decision.focus, "min_score": decision.min_score,
        "failing": decision.failing,
    })
    state["verdict"] = decision.verdict
    state["no_progress"] = (decision.verdict != "FINAL"
                            and _detect_no_progress(state["iterations"], window))
    state["exhausted"] = (decision.verdict != "FINAL"
                          and len(state["iterations"]) >= state["max_iterations"])
    return state


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise RubricError(f"file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise RubricError(f"invalid JSON in {path}: {e}") from e


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _render_state_snapshot(state: dict) -> str:
    """Bounded (<=~12 lines) loop-state snapshot for DCI injection (bounded output)."""
    iters = state.get("iterations", [])
    lines = [f"loop iterations: {len(iters)}/{state.get('max_iterations', DEFAULT_MAX_ITERATIONS)}"]
    if iters:
        last = iters[-1]
        lines.append(f"last verdict: {last['verdict']} · min_score: {last['min_score']}")
        lines.append(f"focus (weakest): {last['focus'] or '— (all criteria pass)'}")
        lines.append(f"failing: {last['failing'] or 'none'}")
        lines.append("scores: " + ", ".join(f"{k}={v}" for k, v in sorted(last["scorecard"].items())))
    if state.get("no_progress"):
        lines.append("⚠ NO-PROGRESS: min_score plateaued — SURFACE to human (do not auto-continue)")
    if state.get("exhausted"):
        lines.append("⚠ EXHAUSTED: max_iterations reached without FINAL — SURFACE to human")
    return "\n".join(lines)


def _cmd_selftest(iso: str) -> int:
    rubric = load_rubric(_load_json(_FIXTURES / "rubric.json"))
    checks: list[tuple[str, bool]] = []

    fin = decide(rubric, _load_json(_FIXTURES / "scorecard-final.json"))
    checks.append(("final_verdict", fin.verdict == "FINAL"))
    checks.append(("final_focus_none", fin.focus is None))

    itr = decide(rubric, _load_json(_FIXTURES / "scorecard-iterating.json"))
    checks.append(("iterating_verdict", itr.verdict == "ITERATING"))
    # fixture is authored so 'readability' is the unique weakest failing criterion
    checks.append(("iterating_focus", itr.focus == "readability"))

    try:
        validate_scorecard(rubric, {})
        checks.append(("malformed_failloud", False))
    except RubricError:
        checks.append(("malformed_failloud", True))

    try:
        decide(rubric, {c.id: 99 for c in rubric})
        checks.append(("out_of_range_failloud", False))
    except RubricError:
        checks.append(("out_of_range_failloud", True))

    ok = all(passed for _, passed in checks)
    trace = {"schema": "loop-kernel-selftest/v1", "iso": iso, "ok": ok,
             "checks": [{"name": n, "pass": p} for n, p in checks]}
    _atomic_write_json(Path(__file__).resolve().parents[1] / "trace" / f"{iso}-selftest.json", trace)
    glyph = "🟢" if ok else "🔴"
    print(f"# loop_kernel selftest {iso} → {glyph}")
    for n, p in checks:
        print(f"  {'PASS' if p else 'FAIL'}  {n}")
    return 0 if ok else 1


def _cmd_decide(args) -> int:
    rubric = load_rubric(_load_json(Path(args.rubric)))
    scorecard = _load_json(Path(args.scorecard))
    decision = decide(rubric, scorecard)
    out = decision.to_dict()
    if args.loop:
        state_path = Path(args.state_dir) / f"{args.loop}.json"
        state = _load_json(state_path) if state_path.exists() else {}
        state = advance(state, args.iso or "NO-ISO", scorecard, decision)
        _atomic_write_json(state_path, state)
        out["loop_state"] = {"iterations": len(state["iterations"]),
                             "no_progress": state["no_progress"], "exhausted": state["exhausted"]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if decision.verdict == "FINAL" else 3


def _cmd_state(args) -> int:
    state_path = Path(args.state_dir) / f"{args.loop}.json"
    if not state_path.exists():
        print(f"[no-loop-state: {args.loop}]")
        return 1
    print(_render_state_snapshot(_load_json(state_path)))
    return 0


def _default_state_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "state"


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="loop_kernel",
                                 description="deterministic DECIDE gate for a self-correcting loop (deterministic)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_self = sub.add_parser("selftest", help="run bundled fixtures, assert kernel correctness (runtime_trace_cmd)")
    p_self.add_argument("--iso", required=True, help="deterministic timestamp (no datetime.now)")

    p_dec = sub.add_parser("decide", help="emit a DECIDE verdict for a rubric+scorecard")
    p_dec.add_argument("--rubric", required=True)
    p_dec.add_argument("--scorecard", required=True)
    p_dec.add_argument("--loop", help="record this iteration into loop-state <loop>.json")
    p_dec.add_argument("--iso", help="iteration timestamp (required-ish when --loop)")
    p_dec.add_argument("--state-dir", default=str(_default_state_dir()))

    p_st = sub.add_parser("state", help="print a bounded loop-state snapshot (DCI injection source)")
    p_st.add_argument("--loop", required=True)
    p_st.add_argument("--state-dir", default=str(_default_state_dir()))

    a = ap.parse_args(argv[1:])
    try:
        if a.cmd == "selftest":
            return _cmd_selftest(a.iso)
        if a.cmd == "decide":
            return _cmd_decide(a)
        if a.cmd == "state":
            return _cmd_state(a)
    except RubricError as e:
        print(f"✗ input error (fail-loud): {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
