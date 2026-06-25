# Recipe — capacity-estimation AS the Judge/evals standard for /self-correcting-loop

> Re-runnable composition (fleet sibling of arch-fitness / ai-era-design-judge). capacity-estimation is the
> **estimate + VERIFY (project)**; `/self-correcting-loop` owns DO + **DECIDE** (loop_kernel). Zero new engine
> (no new engine) — capacity_kernel measures the DR's 5 metrics and PROJECTS them to a loop_kernel scorecard;
> the threshold/iterate DECISION is loop_kernel's. report-only boundary: capacity-estimation is report-only — it never
> buys hardware, edits the design, or auto-accepts FEASIBLE; the human admits the spec + budgets, accepts the verdict.

## Why compose (not reuse the standalone judge)

`capacity_kernel judge` already exits 0/3 (FEASIBLE/INFEASIBLE) = a single loop runnable criterion. But the
**multi-criterion** form below lets the loop's DECIDE return the SPECIFIC binding constraint as `focus` (which of
the 5 DR steps to relieve next) + drive its no-progress / exhaustion guards — i.e. the loop iterates an agent-
system architecture toward feasibility, each round pointed at the binding constraint by loop_kernel.

## A. /self-correcting-loop — CLI-wired (5 deterministic capacity criteria)

Rubric template: [`capacity-estimation.rubric.json`](capacity-estimation.rubric.json) — the 5 DR-step dims as
`runnable` criteria. **The exact-match contract:** `loop_kernel` requires `scorecard keys == rubric ids` EXACTLY,
so the scorecard must carry precisely the rubric's ids — `scorecard --dims` emits exactly those (give each gated
criterion a budget; a criterion with no budget is not constrained and must be dropped from BOTH the rubric and `--dims`).

One iteration (`$CK` = capacity-estimation/src/capacity_kernel.py, `$LK` = self-correcting-loop/src/loop_kernel.py):

```
# PLAN  — read last iteration's focus (the binding DR-step) as this round's repair target:
python3 $LK state --loop <name> --state-dir <dir>

# DO    — relieve that binding constraint on the agent-system design (human/agent edits the SPEC: e.g. enable
#         FP8 KV / raise tensor_parallel / cut context / switch RAG index to SQ8 — capacity-estimation never edits).

# VERIFY — re-estimate CODE/CONFIG vs budgets, project the 5 dims to runnable exit codes:
python3 $CK scorecard --spec <agent-system.spec.json> --budgets <budgets.json> \
  --dims amplification_rpm,token_throughput_tpm,vram_concurrency,prefix_cache_breakeven,rag_ram > <scorecard.json>
# (read the full INFEASIBLE detail — binding constraint + DR macro/micro lever — from `judge` for the DO step:)
python3 $CK judge --spec <agent-system.spec.json> --budgets <budgets.json>; echo EXIT=$?

# DECIDE (deterministic) — keys now match the 5 rubric ids exactly:
python3 $LK decide --rubric <capacity-estimation.rubric.json> --scorecard <scorecard.json> \
  --loop <name> --iso <ISO>; echo EXIT=$?
#   EXIT 0 = FINAL  (all 5 within budget → capacity-feasible) → done
#   EXIT 3 = ITERATING → read `focus` (the binding DR step), go to PLAN (same --loop name accumulates state +
#            no-progress / exhaustion guards). The judge output names the DR lever to apply in the next DO.
```

**Variants:**
- **Subset gating:** budget only the constraints you care about (e.g. just VRAM + RAG) → `--dims vram_concurrency,rag_ram`
  and a rubric.json with only those two ids (keys-==-ids contract).
- **Single-criterion (lightest):** skip the rubric entirely — use `capacity_kernel judge ...; echo EXIT=$?`
  (exit 0/3) as ONE `kind: runnable` criterion inside a larger /self-correcting-loop rubric that also scores
  non-capacity dims. Same deterministic (no LLM-judge) determinism.
- **/autoresearch metric:** the FEASIBLE/INFEASIBLE verdict (or cards_needed / total_vram_gib from `estimate`) is a
  numeric metric for an /autoresearch modify→verify→keep/discard loop over a serving config.

## Honest boundary (a known anti-pattern)
The DECIDE is loop_kernel's; capacity-estimation contributes ONLY the deterministic capacity measurement + the
loop-compatible projection + the DR macro/micro lever text. The semantic question "is THIS the right
architecture for the workload" stays a human/LLM judgment in the loop's DO — never machine-judged here
(anti placebo-fitness).
