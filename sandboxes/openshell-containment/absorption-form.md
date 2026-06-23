---
schema: sandbox-absorption-form/v1
sandbox: openshell-runtime-containment
iso: "2026-06-11"
absorption_chain:
  form: "獨立沙盒落地吸收"   # CONTEXT.md 兩類吸收形式之 ①；最終命名以 slice 01 落地為準
  source_dr: "local_stack/docs/research/自主代理技術的解耦與重構：基於 NVIDIA Open Shell 安全執行期與 LangChain Deep Agents 的零信任架構深度研究報告.md"
  bridge_ref: "<private — northstar skill layer, not mirrored — internal security-architecture mirror>"
  run_records:
    - "data/production/flywheel-runs/2026-06-11-decouple-dr.flywheel-run.yaml"
    - "data/production/flywheel-runs/2026-06-11-decouple-dr.manifest.json"
    - "data/production/flywheel-runs/2026-06-11-adlc-sandbox.flywheel-run.yaml"
  fold_in_targets:
    - "<private — northstar skill layer, not mirrored>"
  land_plan_ref: "docs/plans/2026-06-11-adlc-sandbox"
---

# `openshell-containment` — 吸收形式因果鏈（absorption-form causal chain）

> CONTEXT「吸收形式因果鏈」義：flywheel 從此沙盒**吸收了什麼形式**（C5 那套）。
> **與 `causal-chain.md`（沙盒內因果鏈）是兩份**（用戶明示，禁合併）。
> 鏈進既有 bridge（northstar 私有 skill 層，含內部安全架構 mirror，未隨附）。

## flywheel 吸收的形式

| 形式維度 | 本沙盒吸收進 flywheel 的形式 | join 點 |
|----------|------------------------------|---------|
| **pruning verdicts** | 吸收的核心 = **enforced-containment FORM vs prior policy-by-cooperation**。DR 的 zero-trust thesis 不是「再加一個合作式 hook」，而是把邊界從「LLM 自願走」翻成「policy-governed runtime 強制」。cut：policy-by-cooperation 作為唯一防線 = 不充分（adversarial code 可繞）；adopt：enforced sandbox boundary + 對抗驗證 | bridge `decouple-zero-trust-dr` · PANORAMA |
| **cut_class** | `adopted`（containment 能力本身真落地 + runtime-proven）。對照 solo-pipeline 的 declined/narrowed——此沙盒是純 adopted 的乾淨案例 | — |
| **runtime_comparison** | 硬數據判別形式（placebo-guard discrimination）：permissive policy 下 egress case 會 SUCCEED → predicate flag → count>0；enforced policy 下 BLOCK → count=0。**no-op/permissive sandbox 不能 score 0**——這是吸收進 flywheel 的「evaluator 夠不夠硬」形式（discrimination = G2 前沿度量） | `trace/` · `data/production/containment/2026-06-11-containment-verdict.json`（live: 0 failures） |

## 整合區更高階形式（若本沙盒參與多沙盒組合）

N/A（本 slice）。本沙盒是獨立 containment 能力。整合區 `_integration/` 的完整 ADLC 開發（多沙盒組合，
如 Solo Builder pipeline 整合 Agent 開發）若日後組合本沙盒，其更高階吸收形式（containment 作為組合中的
Runtime-isolation 層）屆時記於整合區，不在此單一能力沙盒。
