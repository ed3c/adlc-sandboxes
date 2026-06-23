# 沙盒全景圖（PANORAMA）— 機械可驗的接線真相

> CONTEXT「全景圖」義：列所有沙盒 + 暴露能力 + 因果鏈鏈接 + wiring 狀態。**機械可驗，非散文**
> （PG-157 presence ≠ consumption 防護：沙盒存在 ≠ 接線）。`fold_in_sandbox_gate.py`（私有 northstar）
> 機械消費下方每個 ```yaml sandbox``` block（不解 markdown 表，那只給人讀）。
>
> ⚠ **誠實邊界（Slop #18）**：本 repo 發佈 **3 個全完成（RIP-proven）真實沙盒**——`openshell-containment`
> / `turbovec` / `self-correcting-loop`。下方標 `(example — not a real sandbox)` 的 block 是 schema 示範，
> gate 跳過 example 與 `_` 前綴目錄。（私有 northstar 另有 `solo-pipeline`（scope narrowed）與
> `_integration/` 整合單元，依完成度門檻**未**納入本公開鏡像。）

## 人讀層（markdown 表）

| Sandbox | Exposed capability | /command | Causal-chain | Absorption-form | Wiring |
|---------|-------------------|----------|--------------|-----------------|--------|
| openshell-containment | enforced-containment exec + adversarial containment_probe | /sandbox-openshell | [link](openshell-containment/causal-chain.md) | [link](openshell-containment/absorption-form.md) | LIVE |
| turbovec | air-gapped local vector search — index+self-query INSIDE ns-sandbox (count_metric==0) | /turbovec | [link](turbovec/causal-chain.md) | [link](turbovec/absorption-form.md) | LIVE |
| self-correcting-loop | deterministic DECIDE gate for a PLAN/DO/VERIFY/DECIDE loop — FINAL iff ∀criterion ≥ threshold, else ITERATING + weakest focus; bounded no-progress/exhaustion guard (DDR-031) | /self-correcting-loop | [link](self-correcting-loop/causal-chain.md) | [link](self-correcting-loop/absorption-form.md) | LIVE |

## 機器層（每沙盒一 block；gate parse 此）

每個真實沙盒在此加一個 ```yaml sandbox``` block。必填 key（gate 機械查完備性）：
`name` / `exposed_capability` / `command` / `triggers` / `launch_precondition` /
`causal_chain` / `absorption_form` / `wiring`。

**wiring 三態（綁定 Runtime Liveness 階梯）**：
- `declared` = dir + SKILL.md + 本 row 存在，未過 fold-in gate（結構在、未驗）。
- `WIRED` = 過靜態 + 問答層（結構合法 + 路由正確），runtime trace 未證。
- `LIVE` = 三層全綠（含 runtime-trace 層真調用 exit 0）。RIP-proven。

```yaml sandbox
# (example — not a real sandbox) — schema 示範用，gate 跳過 name 以 "example" 起或標 example 的 block。
name: example-sandbox
exposed_capability: "schema example only — demonstrates the required keys; no real capability"
command: /example-sandbox
triggers: [example, schema-demo]
launch_precondition: "!`echo precondition-check-here`"
causal_chain: sandboxes/example-sandbox/causal-chain.md
absorption_form: sandboxes/example-sandbox/absorption-form.md
wiring: declared
```

<!-- 真實沙盒 block（openshell-containment / turbovec / self-correcting-loop）。 -->

```yaml sandbox
name: openshell-containment
exposed_capability: "enforced-containment exec under OpenShell default-deny egress + fs isolation, with adversarial containment_probe (3-case, report-only DDR-031, count_metric==0 = fully contained)"
command: /sandbox-openshell   # corrected cc-20260611: /openshell-containment was DOC-ONLY (no .claude/commands file); /sandbox-openshell EXISTS (commit 7e4e262, bounded !-injections + launch contract)
triggers: [containment, sandbox, egress, isolation, openshell]
launch_precondition: "!`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status`"
causal_chain: sandboxes/openshell-containment/causal-chain.md
absorption_form: sandboxes/openshell-containment/absorption-form.md
wiring: LIVE   # slice-03 cc-20260611: static+qa green AND runtime containment_probe exit 0 (gateway Connected, ns-sandbox Ready, 3 cases 0 failures). RIP-proven.
```

```yaml sandbox
name: turbovec
exposed_capability: "air-gapped local vector search — turbovec index+self-query INSIDE ns-sandbox under default-deny egress (count_metric==0 = nothing leaves the machine); composes openshell-containment, offline abi3 wheel staging"
command: /turbovec
triggers: [vector-index, air-gapped-rag, turbovec, embedded-vector, local-rag]
launch_precondition: "!`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status`"
causal_chain: sandboxes/turbovec/causal-chain.md
absorption_form: sandboxes/turbovec/absorption-form.md
wiring: LIVE   # 2026-06-18 instance #3: fold_in_sandbox_gate 3-tier green — static C1-C5 + qa 3/3 + runtime containment_rag_probe exit 0 (recall_at1=1.0 INSIDE ns-sandbox AND egress denied curl (56)/403 → count_metric==0 = air-gapped RAG proven). RIP-proven.
```

```yaml sandbox
name: self-correcting-loop
exposed_capability: "deterministic DECIDE gate for a PLAN/DO/VERIFY/DECIDE self-correcting loop — FINAL iff every rubric criterion score >= its threshold, else ITERATING + weakest-criterion focus; bounded no-progress/exhaustion SURFACE guard (DDR-031, zero LLM-judge). Composes the existing loop layer (autoresearch/refactor-loop), only the DECIDE gate is new."
command: /self-correcting-loop
triggers: [self-correcting-loop, 自我修正迴圈, rubric-gate, plan-do-verify-decide, 迭代收斂]
launch_precondition: "!`python3 --version`"
causal_chain: sandboxes/self-correcting-loop/causal-chain.md
absorption_form: sandboxes/self-correcting-loop/absorption-form.md
wiring: LIVE   # cc-20260623: fold_in_sandbox_gate 4-tier 全綠 — static C1-C6 + qa 5/5 + runtime selftest exit 0 (decide FINAL/ITERATING+focus + 2 fail-loud) + composition N/A. RIP-proven.
```
