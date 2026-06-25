#!/usr/bin/env python3
"""judge_selftest — runtime proof that the fullstack-design-judge rubric COMPOSES the
self-correcting-loop DECIDE kernel (no new engine: no new engine — this sandbox ships a
DR-distilled domain rubric, NOT a second decider).

WHAT IT PROVES (deterministic, runnable as the sandbox-gate runtime_trace_cmd):
  1. composition — calls ../self-correcting-loop/src/loop_kernel.py (the canonical kernel) on
     THIS sandbox's rubric files and prints `CONSUMED:self-correcting-loop` so the absorb gate's
     composition tier (ADR-0009) can machine-verify the dependency was actually consumed.
  2. well-formedness — every rubric file (macro / micro / combined) loads through the kernel and a
     full-pass scorecard yields FINAL (exit 0). A malformed rubric would make the kernel exit 1.
  3. discrimination — a fail scorecard flips the verdict to ITERATING (exit 3) and focuses the right
     criterion, including the runnable-before-low-rubric priority on a MIXED kind rubric (a kernel
     that ignored kind/score would stay FINAL — the discriminating self-check, the issue).
  4. no-drift — combined.rubric.json id-set == macro ∪ micro id-set (the three files stay in sync).

DETERMINISM: no datetime.now/random; the only timestamp is the explicit --iso arg (trace filename).
The kernel is called WITHOUT --loop, so DECIDE is stateless (no state pollution of self-correcting-loop).
Related: sandboxes/fullstack-design-judge/SKILL.md + manifest.yaml.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_SRC = Path(__file__).resolve().parent
_SANDBOX = _SRC.parent                                   # sandboxes/fullstack-design-judge/
_RUBRIC_DIR = _SANDBOX / "recipes"                       # rubric templates live in recipes/ (fleet convention)
_KERNEL = _SANDBOX.parent / "self-correcting-loop" / "src" / "loop_kernel.py"   # the composed engine
_DEP = "self-correcting-loop"

MACRO = _RUBRIC_DIR / "fullstack-design.macro.rubric.json"
MICRO = _RUBRIC_DIR / "fullstack-design.micro.rubric.json"
COMBINED = _RUBRIC_DIR / "fullstack-design.rubric.json"


class SelftestError(Exception):
    """Fail-loud defect (missing dep / malformed rubric / wrong verdict). Never silently swallowed."""


def _load_criteria(path: Path) -> list[dict]:
    if not path.exists():
        raise SelftestError(f"rubric file missing: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    crit = obj.get("criteria") if isinstance(obj, dict) else obj
    if not isinstance(crit, list) or not crit:
        raise SelftestError(f"{path.name}: 'criteria' must be a non-empty list")
    return crit


def _gen_scorecard(criteria: list[dict], fail_ids: tuple[str, ...] = ()) -> dict:
    """A full-pass scorecard (rubric→threshold, runnable→exit 0), flipping any id in fail_ids to fail."""
    sc: dict = {}
    for c in criteria:
        cid = c["id"]
        if c.get("kind", "rubric") == "runnable":
            sc[cid] = 1 if cid in fail_ids else 0                      # exit code: 1 fails, 0 passes
        else:
            thr = int(c.get("threshold", 8))
            sc[cid] = max(1, thr - 3) if cid in fail_ids else thr      # below threshold fails
    return sc


def _decide(rubric_path: Path, scorecard: dict) -> tuple[int, dict]:
    """Invoke the COMPOSED kernel's stateless decide; return (exit_code, parsed_stdout_json)."""
    if not _KERNEL.exists():
        raise SelftestError(f"composed kernel not found at {_KERNEL} — dependency '{_DEP}' is the "
                            f"engine this sandbox reuses; it must be present and LIVE")
    fd, sc_path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(scorecard, f)
        proc = subprocess.run(
            [sys.executable, str(_KERNEL), "decide", "--rubric", str(rubric_path), "--scorecard", sc_path],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(sc_path)
    if proc.returncode == 1:
        raise SelftestError(f"kernel rejected {rubric_path.name} (exit 1): {proc.stderr.strip()}")
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise SelftestError(f"kernel stdout not JSON for {rubric_path.name}: {e}; stdout={proc.stdout!r}")


def run(iso: str) -> int:
    checks: list[tuple[str, bool]] = []
    macro = _load_criteria(MACRO)
    micro = _load_criteria(MICRO)
    combined = _load_criteria(COMBINED)

    # (4) no-drift: combined == macro ∪ micro (sync guard)
    ids = lambda cs: {c["id"] for c in cs}
    drift_ok = ids(combined) == (ids(macro) | ids(micro))
    checks.append(("combined_eq_macro_union_micro", drift_ok))

    # (2) well-formedness: each rubric + full-pass scorecard → FINAL (exit 0)
    for name, path, crit in (("macro", MACRO, macro), ("micro", MICRO, micro), ("combined", COMBINED, combined)):
        code, out = _decide(path, _gen_scorecard(crit))
        checks.append((f"{name}_pass_final", code == 0 and out.get("verdict") == "FINAL"))

    # (3a) discrimination: flip the FIRST combined criterion → ITERATING, focus == it
    first_id = combined[0]["id"]
    code, out = _decide(COMBINED, _gen_scorecard(combined, fail_ids=(first_id,)))
    checks.append(("single_fail_iterating", code == 3 and out.get("verdict") == "ITERATING"))
    checks.append(("single_fail_focus", out.get("focus") == first_id))

    # (3b) runnable-priority on a MIXED rubric: a failing runnable (effective 0) focuses BEFORE a low
    #      rubric score — a kernel ignoring kind would focus the rubric one. Discriminating self-check.
    code, out = _decide(COMBINED, _gen_scorecard(combined, fail_ids=(first_id, "c_tests_pass")))
    checks.append(("runnable_priority_focus", code == 3 and out.get("focus") == "c_tests_pass"))

    ok = all(p for _, p in checks)
    # (1) composition marker — REQUIRED in stdout for the absorb gate composition tier (ADR-0009/the issue)
    print(f"CONSUMED:{_DEP}")
    trace = {"schema": "fullstack-design-judge-selftest/v1", "iso": iso, "ok": ok,
             "composed_kernel": str(_KERNEL.relative_to(_SANDBOX.parent)),
             "checks": [{"name": n, "pass": p} for n, p in checks]}
    trace_path = _SANDBOX / "trace" / f"{iso}-judge-selftest.json"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = trace_path.with_name(trace_path.name + ".tmp")
    tmp.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, trace_path)

    print(f"# fullstack-design-judge selftest {iso} → {'🟢' if ok else '🔴'} "
          f"(composes {_DEP} kernel; {len(combined)} criteria)")
    for n, p in checks:
        print(f"  {'PASS' if p else 'FAIL'}  {n}")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="judge_selftest",
                                 description="runtime proof: fullstack-design rubric composes the self-correcting-loop kernel")
    ap.add_argument("--iso", required=True, help="deterministic timestamp (no datetime.now)")
    args = ap.parse_args(argv[1:])
    try:
        return run(args.iso)
    except SelftestError as e:
        print(f"✗ selftest fail-loud: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
