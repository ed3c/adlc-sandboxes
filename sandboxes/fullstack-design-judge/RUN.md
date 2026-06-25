# fullstack-design-judge — RUN (real transcript)

> A DR-distilled Judge/evals rubric (10 macro architecture axes + 11 micro code axes) for a distributed
> frontend/backend + BFF + AI-agent-async system. The **only new thing is the rubric** — DECIDE is delegated
> to the `self-correcting-loop` kernel (no second decider). Report-only — a human admits the judged artifact +
> rubric and accepts FINAL; the kernel only decides FINAL/ITERATING from the claimed scores.
>
> Source DR: [`現代分散式系統架構下前後端需求拆分、BFF 模式演進與 AI Agent 異步任務調度之深度技術研究報告.md`](../../research/現代分散式系統架構下前後端需求拆分、BFF%20模式演進與%20AI%20Agent%20異步任務調度之深度技術研究報告.md)
> · 一條命令復現：`python3 src/judge_selftest.py --iso 2026-06-24`（無 Docker / 無網路 / 無 Ollama）。

## selftest — 🟢, and it CONSUMES the self-correcting-loop kernel (composition is proven, not claimed)

```
$ python3 src/judge_selftest.py --iso 2026-06-24
CONSUMED:self-correcting-loop
# fullstack-design-judge selftest 2026-06-24 → 🟢 (composes self-correcting-loop kernel; 21 criteria)
  PASS  combined_eq_macro_union_micro
  PASS  macro_pass_final
  PASS  micro_pass_final
  PASS  combined_pass_final
  PASS  single_fail_iterating
  PASS  single_fail_focus
  PASS  runnable_priority_focus
# exit 0
```

The `CONSUMED:self-correcting-loop` marker is printed by actually loading and calling
`sandboxes/self-correcting-loop/src/loop_kernel.py` — the composition (`requires: [self-correcting-loop]`) is
mechanically entailed by the runtime trace, not asserted. `combined_eq_macro_union_micro` proves the merged
rubric is exactly `macro ∪ micro` (no drift). `single_fail_iterating` / `single_fail_focus` prove the loop
returns ITERATING + the weakest axis when one criterion fails; `runnable_priority_focus` proves a failing
`runnable` (exit-code) axis is prioritized over a low-scoring `rubric` axis.

## The rubric (the intellectual product)

- `recipes/fullstack-design.macro.rubric.json` — 10 macro architecture axes (zero-trust boundary, contract-first
  SSOT, separation-of-concerns, concurrency control, BFF aggregation, BFF-vs-Gateway split, BFF-OAuth topology,
  async decoupling, protocol trade-offs, parallel fan-out), all `kind: rubric` (architecture-judgment semantics).
- `recipes/fullstack-design.micro.rubric.json` — 11 micro code axes, **mixed**: machine-checkable ones
  (reject-negatives / shared-schema-no-dup / contract-tests / atomic-concurrency / idempotency / cookie-4-attrs /
  tests-pass) are `kind: runnable` (zero-LLM, exit-code); irreducibly-semantic ones (FE holds no authoritative
  compute / parallel-not-serial / stream resilience / task observability) stay `kind: rubric`.
- `recipes/fullstack-design.rubric.json` — the merged 21-criterion rubric.

## Two-tier flow

Converge the **macro architecture** first (`.macro.` → FINAL = every architecture axis ≥ threshold), then the
**micro code** (`.micro.`), or run the merged rubric for a single full-compliance check — guiding macro design
down to micro implementation. DECIDE is the deterministic `self-correcting-loop` kernel each round.

## Honest boundary

- This sandbox is honestly a **thin domain delta over `self-correcting-loop`** (as sandcastle is to openshell):
  the loop engine is reused, not rebuilt; the only new thing is the DR-distilled rubric.
- The kernel guarantees FINAL is mechanically entailed by the **claimed** scores; it does **not** guarantee the
  scores themselves are honest — scoring is the LLM/human VERIFY responsibility.
- A `runnable` criterion needs a real artifact's code/tests to produce a real exit code; for a pure design doc
  (no code) use the `.macro.` rubric — do not claim a runnable axis passed on something with no code.
- Opinionated claims are written conditionally (external-verified): "SSE is best" / "fan-out 60-70%" are not
  absolute — the rubric asks "if you choose X, handle cost Y / state the claim precisely" (RFC/IETF/OWASP anchors).
