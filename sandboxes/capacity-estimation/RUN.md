# capacity-estimation — RUN (real transcript)

> Deterministic AI-Agent capacity estimator + feasibility rubric judge. Given an agent-system spec it
> computes the DR's five core metrics and JUDGES feasibility against budgets — FEASIBLE iff every budgeted
> criterion is within budget, else INFEASIBLE + the binding constraint + the macro (GPU/TP/RAM) and micro
> (PagedAttention/FP8-KV/RadixAttention/SQ8/DiskANN) levers. Report-only — a human admits the spec/budgets
> and accepts the architecture decision; the kernel only computes numbers and compares them to budgets.
>
> Source DR: [`AI Agent 時代的計算系統容量估算與架構設計研究報告.md`](../../research/AI%20Agent%20時代的計算系統容量估算與架構設計研究報告.md)
> · 一條命令復現：`python3 src/capacity_kernel.py selftest --iso 2026-06-24`（無 Docker / 無網路 / 無 Ollama）。

## 1. selftest — 20/20 🟢 (faithfully reproduces the DR's worked example + judge discrimination)

```
$ python3 src/capacity_kernel.py selftest --iso 2026-06-24
  PASS  output_tps_20k
  PASS  weights_140gb_decimal
  PASS  kv_per_token_327680_bytes_exact
  PASS  kv_total_40gib_binary
  PASS  rag_raw_122_88gb_decimal
  PASS  rag_index_184_32gb_decimal
  PASS  judge_feasible_when_budgets_met
  PASS  judge_infeasible_when_vram_tight
  PASS  binding_is_vram
  PASS  binding_carries_micro_lever
  PASS  prefix_cache_below_breakeven_binds
  PASS  index_default_hnsw
  PASS  index_recall_latency_picks_sq8
  PASS  spec_decode_binds_above_ceiling
  PASS  spec_decode_ok_at_ceiling
  PASS  scorecard_keys_are_the_5_criteria
  PASS  scorecard_values_are_exit_codes
  PASS  scorecard_vram_binds_exit1
  PASS  scorecard_within_budget_exit0
  PASS  malformed_failloud
# exit 0
```

## 2. estimate — the DR's worked example (自動化數據分析 Agent, Llama-3-70B)

```
$ python3 src/capacity_kernel.py estimate --spec src/fixtures/dr-example-spec.json
{
  "step1_amplification": { "agent_qps": 40, "rpm_equiv": 2400 },
  "step2_throughput": { "input_tps": 120000, "output_tps": 20000, "total_tps": 140000 },
  "step3_vram": {
    "weights": { "gb": 140.0, "gib": 130.39 },
    "kv_per_token_bytes": 327680,
    "kv_total": { "gb": 42.95, "gib": 40.0 },
    "total_vram": { "gb": 182.95, "gib": 170.39 },
    "card_vram_gb": 80, "cards_needed": 3
  },
  "step4_prefix_cache": { "breakeven": 0.3 },
  "step5_rag": {
    "raw": { "gb": 122.88 }, "with_index": { "gb": 184.32 },
    "recommended_index": { "index": "HNSW float32", "recall": "98-99%", "p95_ms": "1-5" }
  }
}
```

Every number is an EXACT function of the spec (bytes computed precisely, then GiB + GB dual-unit) — the DR
mixes decimal GB and binary GiB; the kernel normalizes to bytes and reports both. The `selftest` asserts each
value against the DR's printed worked example (`weights_140gb`, `kv_per_token_327680_bytes_exact`, …).

## 3. judge — feasibility is an exit code, not prose

`judge --spec S.json --budgets B.json` exits `0`=FEASIBLE / `3`=INFEASIBLE. INFEASIBLE lists each binding
constraint with the macro architecture lever (cards / tensor-parallel / vector-DB RAM) AND the micro code
lever (PagedAttention / FP8 KV quant / RadixAttention / SQ8 / DiskANN). A criterion with no budget is marked
`not_constrained` (informational, never fails) — a partial budget never fabricates a verdict. The selftest
proves both directions (`judge_feasible_when_budgets_met`, `judge_infeasible_when_vram_tight`,
`binding_is_vram`, `binding_carries_micro_lever`).

## 4. AS a loop criterion

`scorecard` projects the 5 budgeted criteria to a `self-correcting-loop`-compatible runnable scorecard
(`{id: exit_code}`; 0 = within budget, 1 = BINDING) — so a self-correcting loop iterating an agent-system
architecture gets one deterministic "capacity-feasible" axis whose `focus` points at the binding DR step.
The cross-kernel test (`test_scorecard_projection_is_loop_kernel_compatible`) runs the projection through the
**actual** `sandboxes/self-correcting-loop` kernel — green.

## Honest boundary

- The kernel is a **back-of-envelope estimator** (the DR's own positioning), not a real vLLM/SGLang benchmark.
- It computes numbers + names binding constraints + suggests levers; **buying cards / enabling FP8 is a human
  decision**, never auto-applied.
- The optimization techniques (PagedAttention/RadixAttention/SQ8/DiskANN) are cited for their quantified
  effect as levers — the kernel does not re-implement those engines.
