#!/usr/bin/env python3
"""scorecard_template — emit a scorecard skeleton whose keys EXACTLY match a rubric's criterion ids.

WHY: loop_kernel.decide requires `scorecard keys == rubric ids` EXACTLY (missing OR extra both fail-loud).
Driving the fullstack-design loop by hand over a 10/11/21-criterion rubric, it is easy to miss an id. This
emits the full id set with FILL placeholders so VERIFY just replaces each value — a runnable criterion →
an exit code (int, 0 = pass), a rubric criterion → an int 1-10. The placeholders are deliberately NON-int
strings, so the kernel fail-louds until you fill REAL scores: you cannot run the loop without actually
scoring each axis (anti-placebo-fitness, the issue). Pairs with recipes/with-self-correcting-loop.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="scorecard_template",
        description="emit a scorecard skeleton with keys == rubric ids (the loop_kernel exact-match contract)")
    ap.add_argument("--rubric", required=True, help="path to a fullstack-design rubric JSON (macro/micro/combined)")
    args = ap.parse_args(argv[1:])
    try:
        obj = json.loads(Path(args.rubric).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"✗ cannot read rubric {args.rubric}: {e}", file=sys.stderr)
        return 1
    crit = obj.get("criteria") if isinstance(obj, dict) else obj
    if not isinstance(crit, list) or not crit:
        print(f"✗ rubric {args.rubric} has no non-empty 'criteria' list", file=sys.stderr)
        return 1
    sc: dict = {}
    for c in crit:
        kind = c.get("kind", "rubric")
        sc[c["id"]] = ("FILL:runnable-exit-code(int,0=pass)" if kind == "runnable"
                       else "FILL:rubric-score(int,1-10)")
    print(json.dumps(sc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
