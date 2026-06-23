# 沙盒全景圖（PANORAMA）— 機器可解的接線真相

> 「全景圖」義：列所有沙盒 + 暴露能力 + 啟動方式 + wiring 狀態。**機器可解**（下方每個 ```yaml sandbox```
> block 都可程式解析），人讀的 markdown 表只給人看。存在 ≠ 接線——以 `wiring` 狀態為準。
>
> 本 repo 有 **3 個真實沙盒**——`openshell-containment` / `turbovec` / `self-correcting-loop`。下方標
> `(example — not a real sandbox)` 的 block 是 schema 示範。

## 人讀層（markdown 表）

| Sandbox | Exposed capability | /command | Wiring |
|---------|-------------------|----------|--------|
| openshell-containment | enforced-containment exec + adversarial containment_probe | /sandbox-openshell | LIVE |
| turbovec | air-gapped local vector search — index+self-query INSIDE ns-sandbox (count_metric==0) | /turbovec | LIVE |
| self-correcting-loop | deterministic DECIDE gate for a PLAN/DO/VERIFY/DECIDE loop — FINAL iff ∀criterion ≥ threshold, else ITERATING + weakest focus; bounded no-progress/exhaustion guard | /self-correcting-loop | LIVE |

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
