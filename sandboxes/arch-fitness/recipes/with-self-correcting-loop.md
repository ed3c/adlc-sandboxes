# Recipe — arch-fitness AS the Judge/evals standard for /self-correcting-loop (and director for /refactor-loop)

> Re-runnable composition. arch-fitness is the **VERIFY + Judge**; the loop owns DO + DECIDE. Zero new engine
> (compose the existing loop layer, do not duplicate it). All commands below are runtime-proven. arch-fitness is
> report-only — it never edits the target and never auto-accepts FINAL; the human admits the target + spec.

## A. /self-correcting-loop — CLI-wired (one loop, deterministic + semantic criteria together)

Rubric template: [`arch-fitness.rubric.json`](arch-fitness.rubric.json) — 5 deterministic `runnable` dims
(gated) + 3 `semantic` `rubric` dims (LLM-scored). **coupling_distance is deliberately NOT gated** (it is a
surfaced diagnostic — a concrete+stable leaf legitimately sits at D→1; read it from the report, do not gate).

**The exact-match contract:** `loop_kernel` requires `scorecard keys == rubric ids` EXACTLY (missing/extra
both fail). So the scorecard must carry precisely the rubric's 8 ids — `scorecard --dims` emits the 5
deterministic ones; the LLM appends the 3 semantic scores in VERIFY.

One iteration (`$K` = arch_fitness_kernel.py, `$LK` = self-correcting-loop/src/loop_kernel.py):

```
# PLAN  — read last iteration's focus (the weakest dim) as this round's repair target:
python3 $LK state --loop <name> --state-dir <dir>

# DO    — improve the target codebase toward that focus (human/agent edits; arch-fitness never edits).

# VERIFY (deterministic half) — measure CODE vs MODEL, project the 5 gated dims to exit codes:
python3 $K measure --target <repo> --spec <arch-model.yaml> --iso <ISO> --report <report.json>
python3 $K scorecard --report <report.json> \
  --dims layer_dependency,module_boundary,long_method,too_many_params,large_class > <scorecard.json>
# VERIFY (semantic half) — the LLM scores the 3 semantic criteria 1-10 and APPENDS them into <scorecard.json>:
#   module_depth, self_documenting_vs_comments, define_errors_out_of_existence
#   (judge against the rubric() guidance; these are NOT machine-measurable — anti placebo-fitness)

# DECIDE (deterministic) — keys now match the 8 rubric ids exactly:
python3 $LK decide --rubric <arch-fitness.rubric.json> --scorecard <scorecard.json> \
  --loop <name> --iso <ISO>; echo EXIT=$?
#   EXIT 0 = FINAL (all 5 deterministic exit 0 AND all 3 semantic >= threshold 8) → done
#   EXIT 3 = ITERATING → read `focus`, go to PLAN (same --loop name accumulates state + no-progress/exhaust guards)
```

**Variants:**
- *Deterministic-only loop* (no LLM judging): drop the 3 `semantic` entries from the rubric and the `--dims`
  list stays the same 5 → scorecard feeds `decide` with zero surgery.
- *Strict-coupling loop* (drive Zone-of-Pain → 0): add `coupling_distance` to both the rubric (`runnable`)
  and the `--dims` list.

## B. /refactor-loop — recipe-level (arch-fitness DIRECTS, does not wire)

Different axis, complementary: arch-fitness = macro/structural (which module violates a boundary / is in the
Zone of Pain / is a Large Class); /refactor-loop = micro/mechanical (per-function radon complexity, behavior-locked).

```
python3 $K measure ... → focus + large_classes[] + zone-of-pain components   # WHERE to refactor
   → run /refactor-loop on those specific modules                            # HOW (behavior-locked, radon-judged)
   → re-run $K measure → confirm the structural smell dropped                # re-VERIFY
```

⚠ **Orthogonality caveat:** arch-fitness `large_class` counts methods/SRP; /refactor-loop's radon counts
cyclomatic complexity. A class can be `large_class`-flagged yet `radon avg ≤ 3` → /refactor-loop rules it
`characterize_only` (refactor = vanity). The two signals are independent; the human reconciles — do not treat
arch-fitness `large_class` as "must refactor".

## report-only boundary (both)
arch-fitness only VERIFIES / directs. `target + rubric/spec admitted by human`; `FINAL decided by the
deterministic loop kernel`; `no_progress / exhausted → SURFACE to human`, never auto-continue, never auto-edit.
