# 沙盒全景圖（PANORAMA）— 機器可解的接線真相

> 「全景圖」義：列所有沙盒 + 暴露能力 + 啟動方式 + wiring 狀態。**機器可解**（下方每個 ```yaml sandbox```
> block 都可程式解析），人讀的 markdown 表只給人看。存在 ≠ 接線——以 `wiring` 狀態為準。
>
> 本 repo 有 **7 個真實沙盒**——`openshell-containment` / `turbovec` / `self-correcting-loop` /
> `sandcastle-orchestration` / `arch-fitness` / `capacity-estimation` / `fullstack-design-judge`。下方標
> `(example — not a real sandbox)` 的 block 是 schema 示範。

## 人讀層（markdown 表）

| Sandbox | Exposed capability | /command | Wiring |
|---------|-------------------|----------|--------|
| openshell-containment | enforced-containment exec + adversarial containment_probe | /sandbox-openshell | LIVE |
| turbovec | air-gapped local vector search — index+self-query INSIDE ns-sandbox (count_metric==0) | /turbovec | LIVE |
| self-correcting-loop | deterministic DECIDE gate for a PLAN/DO/VERIFY/DECIDE loop — FINAL iff ∀criterion ≥ threshold, else ITERATING + weakest focus; bounded no-progress/exhaustion guard | /self-correcting-loop | LIVE |
| sandcastle-orchestration | run sandcastle's working composition (head-run container-isolated agent + host-git branch/commit = merge-back outcome + host exec-gate) against a fixture/throwaway repo, project to a deterministic observation-record | /sandcastle-orchestration | LIVE |
| arch-fitness | deterministic architecture-fitness Judge/evals standard — measure CODE vs an arch-model spec → Clean-Arch layer + module-boundary violations + Martin I/A/D coupling + AST smells; PASS iff 0 hard violations; AS the VERIFY/Judge for a self-correcting loop | /arch-fitness | LIVE |
| capacity-estimation | deterministic AI-Agent capacity estimator + feasibility rubric judge — 5 DR metrics (Agent QPS / token TPS / VRAM=weights+KV / prefix-cache breakeven / RAG RAM); FEASIBLE iff every budgeted criterion within budget, else INFEASIBLE + binding constraint + macro/micro lever; projects to a self-correcting-loop runnable scorecard | /capacity-estimation | LIVE |
| fullstack-design-judge | DR-distilled Judge rubric (10 macro architecture + 11 micro code axes) for a distributed FE/BE + BFF + agent-async system; DECIDE delegated to the self-correcting-loop kernel (CONSUMED:self-correcting-loop proven); guides macro design → micro code | /fullstack-design-judge | LIVE |

## 機器層（每沙盒一 block）

每個真實沙盒在此加一個 ```yaml sandbox``` block。必填 key：
`name` / `exposed_capability` / `command` / `triggers` / `launch_precondition` / `wiring`。

**wiring 三態（綁定 Runtime Liveness 階梯）**：
- `declared` = dir + SKILL.md + 本 row 存在，未驗證（結構在、未驗）。
- `WIRED` = 過靜態 + 問答層（結構合法 + 路由正確），runtime trace 未證。
- `LIVE` = 三層全綠（含 runtime-trace 層真調用 exit 0）。runtime-proven。

```yaml sandbox
# (example — not a real sandbox) — schema 示範用。
name: example-sandbox
exposed_capability: "schema example only — demonstrates the required keys; no real capability"
command: /example-sandbox
triggers: [example, schema-demo]
launch_precondition: "!`echo precondition-check-here`"
wiring: declared
```

<!-- 真實沙盒 block（openshell-containment / turbovec / self-correcting-loop）。 -->

```yaml sandbox
name: openshell-containment
exposed_capability: "enforced-containment exec under OpenShell default-deny egress + fs isolation, with adversarial containment_probe (3-case, report-only, deterministic, count_metric==0 = fully contained)"
command: /sandbox-openshell   # /openshell-containment is a DOC-ONLY alias; the real entry is /sandbox-openshell (bounded !-injections + launch contract)
triggers: [containment, sandbox, egress, isolation, openshell]
launch_precondition: "!`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status`"
wiring: LIVE   # static+qa green AND runtime containment_probe exit 0 (gateway Connected, ns-sandbox Ready, 3 cases 0 failures). runtime-proven.
```

```yaml sandbox
name: turbovec
exposed_capability: "air-gapped local vector search — turbovec index+self-query INSIDE ns-sandbox under default-deny egress (count_metric==0 = nothing leaves the machine); composes openshell-containment, offline abi3 wheel staging"
command: /turbovec
triggers: [vector-index, air-gapped-rag, turbovec, embedded-vector, local-rag]
launch_precondition: "!`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status`"
wiring: LIVE   # static + qa 3/3 + runtime containment_rag_probe exit 0 (recall_at1=1.0 INSIDE ns-sandbox AND egress denied curl (56)/403 → count_metric==0 = air-gapped RAG proven). runtime-proven.
```

```yaml sandbox
name: self-correcting-loop
exposed_capability: "deterministic DECIDE gate for a PLAN/DO/VERIFY/DECIDE self-correcting loop — FINAL iff every rubric criterion score >= its threshold, else ITERATING + weakest-criterion focus; bounded no-progress/exhaustion SURFACE guard (deterministic, zero LLM-judge). Composes the existing loop layer (autoresearch/refactor-loop), only the DECIDE gate is new."
command: /self-correcting-loop
triggers: [self-correcting-loop, 自我修正迴圈, rubric-gate, plan-do-verify-decide, 迭代收斂]
launch_precondition: "!`python3 --version`"
wiring: LIVE   # static + qa 5/5 + runtime selftest exit 0 (decide FINAL/ITERATING+focus + 2 fail-loud). runtime-proven.
```

```yaml sandbox
name: sandcastle-orchestration
exposed_capability: "run @ai-hero/sandcastle's working composition — sandcastle head-run (container-isolated agent execution) + host-side plain git (branch/commit = the merge-back OUTCOME) + host-side exec-gate (node --test between stages) — against a fixture/throwaway repo, then project the rip-result.json into a deterministic observation-record (boundary_adapter.py, pure python). Deliberately avoids sandcastle's own worktree merge-back (broken on macOS docker, gitdir patch is Windows-only). Honest thin delta: the container-isolated half ≈ a generic containment sandbox; the real delta is sandcastle's orchestration design contract."
command: /sandcastle-orchestration
triggers: [sandcastle, container-isolated agent orchestration, 招牌組合, agent-orchestration RIP study vehicle, exec-gate, observation-record, sandcastle-orchestration]
launch_precondition: "!`timeout 5 docker info --format '{{.ServerVersion}}' 2>&1 | head -1 || echo '[docker-down]'`"
wiring: LIVE   # static + qa 6/6 + runtime boundary_adapter selftest exit 0 (Path B deterministic projection, runtime-proven). Path A (the probabilistic RIP run) additionally needs Docker + Node + a Claude OAuth token — see RUN.md honest boundary.
```

```yaml sandbox
name: arch-fitness
exposed_capability: "deterministic architecture-fitness Judge/evals standard — measure a target source tree (CODE) vs a declared arch-model spec (MODEL): Clean-Arch layer-dependency violations + modular-monolith module-boundary breaches + Martin I/A/D coupling (Zone-of-Pain, surfaced-not-gated) + AST code smells (Long Method/Too Many Params/Large Class). verdict PASS iff 0 hard violations; focus = weakest dim. Report-only — never edits the target, never auto-accepts. AS the VERIFY/Judge for a self-correcting loop (loop owns DO+DECIDE); composes the existing loop layer, no new engine."
command: /arch-fitness
triggers: [arch-fitness, 架構適應度, architecture-erosion, model-code-gap, layer-dependency, fitness-function]
launch_precondition: "!`python3 --version`"
wiring: LIVE   # static + qa 27/27 + runtime selftest exit 0 (13 dims discriminated, sample→FAIL/clean→PASS). runtime-proven.
```

```yaml sandbox
name: capacity-estimation
exposed_capability: "deterministic AI-Agent capacity estimator + feasibility rubric judge — computes the DR's five core metrics (Agent QPS amplification, Input/Output token TPS, GPU VRAM = weights + KV cache, prefix-cache breakeven, RAG vector-DB RAM) and JUDGES feasibility against budgets: FEASIBLE iff every budgeted criterion within budget, else INFEASIBLE + binding constraint + macro architecture lever (GPU cards / tensor-parallel / vector-DB RAM) AND micro code lever (PagedAttention / FP8 KV / RadixAttention / SQ8 / DiskANN). Report-only — spec/budgets admitted by human, the buy/enable decision is human. Projects to a self-correcting-loop runnable scorecard."
command: /capacity-estimation
triggers: [capacity-estimation, 容量估算, agent-capacity, vram-sizing, kv-cache, token-throughput, gpu-sizing, capacity-feasibility]
launch_precondition: "!`python3 --version`"
wiring: LIVE   # static + qa 50/50 + runtime selftest exit 0 (20 cases: faithful DR worked-example + judge discrimination + cross-kernel scorecard projection). runtime-proven.
```

```yaml sandbox
name: fullstack-design-judge
exposed_capability: "DR-distilled fullstack-design Judge rubric (10 macro architecture axes + 11 micro code axes, runnable/rubric kind split) for a distributed frontend/backend + BFF + AI-agent-async system DESIGN or CODE. The only new thing is the rubric — DECIDE is delegated to the self-correcting-loop kernel (requires: [self-correcting-loop]; CONSUMED:self-correcting-loop printed in the runtime trace). Two-tier flow guides macro architecture down to micro code. Report-only — judged artifact + rubric admitted by human, FINAL accepted by human."
command: /fullstack-design-judge
triggers: [fullstack-design-judge, 分散式設計評判, BFF設計評判, 前後端架構評判, 系統設計rubric, design-judge]
launch_precondition: "!`python3 --version`"
wiring: LIVE   # static + runtime judge_selftest exit 0 (7 cases incl. CONSUMED:self-correcting-loop + combined==macro∪micro + ITERATING/focus). runtime-proven.
```
