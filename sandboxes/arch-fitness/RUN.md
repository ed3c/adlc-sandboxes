# arch-fitness — RUN (real transcript)

> Deterministic architecture-fitness Judge/evals standard: measure a target source tree (CODE) against a
> declared arch-model spec (MODEL) and surface the model-code gap. Report-only — it never edits the target
> and never auto-accepts a verdict; a human admits the target + spec, a human/loop decides what to change.
>
> Source DR: [`軟體架構的戰略與戰術雙重奏…系統性研究.md`](../../research/軟體架構的戰略與戰術雙重奏：從領域邊界劃分到代碼演進治理的系統性研究.md)
> · 一條命令復現：`python3 src/arch_fitness_kernel.py selftest --iso 2026-06-24`（無 Docker / 無網路 / 無 Ollama）。

## 1. selftest — 13/13 🟢 (the kernel discriminates every dimension)

```
$ python3 src/arch_fitness_kernel.py selftest --iso 2026-06-24
# arch_fitness_kernel selftest 2026-06-24 → 🟢
  PASS  layer_violation_detected
  PASS  both_boundary_breaches
  PASS  long_method_detected
  PASS  too_many_params_detected
  PASS  large_class_detected
  PASS  persistence_zone_pain
  PASS  sample_verdict_fail
  PASS  focus_is_hard_dim
  PASS  clean_verdict_pass
  PASS  clean_focus_none
  PASS  spec_failloud
  PASS  rubric_three_axes
  PASS  rubric_det_dims_real
# exit 0
```

The selftest measures two bundled fixtures — `fixtures/sample_project` (intentionally dirty) and
`fixtures/clean_project` (clean) — and asserts the kernel calls each correctly. A PASS is entailed by the
real measurement, never by a prose claim (zero LLM-judge).

## 2. measure — the dirty fixture is called FAIL with the real violations

```
$ python3 src/arch_fitness_kernel.py measure \
    --target fixtures/sample_project --spec fixtures/sample_project.arch.yaml --iso 2026-06-24
{
  "schema": "arch-fitness-report/v1",
  "verdict": "FAIL",
  "focus": "layer_dependency",
  "layer_violations": [
    { "from": "controllers", "to": "persistence",
      "file": "app/controllers/order_controller.py", "lineno": 2 }
  ],
  "boundary_violations": [
    { "component": "controllers", "imports": "persistence",
      "file": "app/controllers/order_controller.py", "lineno": 2 },
    { "component": "workflow", "imports": "controllers",
      "file": "app/workflow/order_workflow.py", "lineno": 3 }
  ],
  "coupling": { "controllers": { "ca": 1, "ce": 2, ... } }
  ...
}
```

`verdict=FAIL` iff there is ≥1 hard (layer + boundary) violation; `focus` = the weakest dimension, which a
self-correcting loop uses as the next round's repair target. The clean fixture returns `verdict=PASS`,
`focus=none` (covered by `clean_verdict_pass` / `clean_focus_none` above).

## 3. AS a Judge/evals standard for a loop

arch-fitness is the **VERIFY + Judge**; a self-correcting loop owns DO + DECIDE. The
[`recipes/with-self-correcting-loop.md`](recipes/with-self-correcting-loop.md) recipe wires the 5 deterministic
`runnable` dims (gated by exit code) + 3 `semantic` `rubric` dims (LLM-scored) into one loop whose DECIDE is
the deterministic `self-correcting-loop` kernel (`sandboxes/self-correcting-loop`). The kernel measures the
deterministic subset; the semantic concepts stay LLM-scored in the loop's VERIFY.

## Honest boundary

- arch-fitness measures **structure** (layer/boundary/coupling + AST smells); it does not judge runtime
  behavior or correctness.
- `coupling_distance` (Martin Zone-of-Pain) is **surfaced, not gated** — a concrete+stable leaf legitimately
  sits in the Zone of Pain; read it from the report, do not auto-fail on it.
- `large_class` counts methods/SRP, which is a **different axis** from cyclomatic complexity — a flagged class
  can still be `radon avg ≤ 3`. The two signals are independent; a human reconciles.
