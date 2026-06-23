---
schema: sandbox-causal-chain/v1
sandbox: openshell-runtime-containment
iso: "2026-06-11"
chain:
  - concept: "執行期容管法則的 Runtime 層入口：idempotent gateway bootstrap（9-layer macOS same-path fix），mTLS Connected + sandbox Ready 即 launch contract"
    landed_artifact: "sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh"
    wiring_ref: "<private — northstar skill layer, not mirrored>"
    wiring_anchor: "openshell_gateway_bootstrap"
    runtime_evidence_ref: "execution/state/adlc-sandbox-scaffold-trace.jsonl"
    iso: "2026-06-11"
  - concept: "沙盒執行入口：thin openshell-exec wrapper（run_in_sandbox / SandboxResult），所有沙盒消費走它"
    landed_artifact: "sandboxes/openshell-containment/src/sandbox_runner.py"
    wiring_ref: "sandboxes/openshell-containment/src/containment_probe.py"
    wiring_anchor: "run_in_sandbox"
    runtime_evidence_ref: "execution/state/adlc-sandbox-scaffold-trace.jsonl"
    iso: "2026-06-11"
  - concept: "Test phase 對抗 containment 驗證（report-only, DDR-031）：adversarial egress/fs + legit 三案"
    landed_artifact: "sandboxes/openshell-containment/src/containment_probe.py"
    wiring_ref: "sandboxes/openshell-containment/tests/test_containment_probe.py"
    wiring_anchor: "run_probe"
    runtime_evidence_ref: "data/production/containment/2026-06-11-containment-verdict.json"
    iso: "2026-06-11"
  - concept: "Monitor: PG-143 standing sentinel（RIP guard——能力刪除 → count<3 → unresolved → standing_monitor 翻紅）"
    landed_artifact: "<private — northstar execution layer, not mirrored>"
    wiring_ref: "<private — northstar execution layer, not mirrored>"
    wiring_anchor: "standing-health-probes.yaml"
    runtime_evidence_ref: "data/production/standing-monitor-state.json"
    iso: "2026-06-11"
  - concept: "fold-in 定位提升：Model-Runtime-Harness 三層解耦節（cohere+name，Runtime 層 LIVE）+ Declined 表 supersession"
    landed_artifact: "<private — northstar skill layer, not mirrored>"
    wiring_ref: "<private — northstar skill layer, not mirrored — internal security-architecture mirror>"
    wiring_anchor: "adlc-lifecycle"
    runtime_evidence_ref: "data/production/flywheel-runs/2026-06-11-adlc-sandbox.flywheel-run.yaml"
    iso: "2026-06-11"
  - concept: "Promote：R=0 promotion gate 過 + redset-attribution 機械 record（git-cycle-merge Rule 11）"
    landed_artifact: "data/production/promotion-records/2026-06-11-worktree-flywheel-adlc-deepagents.redset-attribution.yaml"
    wiring_ref: ".claude/rules/git-cycle-merge.md"
    wiring_anchor: "redset_attribution"
    runtime_evidence_ref: "data/production/promotion-records/2026-06-11-worktree-flywheel-adlc-deepagents.redset-attribution.yaml"
    iso: "2026-06-11"
  - concept: "沙盒接口 /command（flywheel 消費路徑，PG-157 閉合）：launch contract + Dynamic Context Injection 實時狀態"
    landed_artifact: ".claude/commands/sandbox-openshell.md"
    wiring_ref: "<private — northstar skill layer, not mirrored>"
    wiring_anchor: "sandbox-openshell"
    runtime_evidence_ref: "data/production/telemetry/cac-trace-c89779c5-3ede-4e81-acf1-04842f3fe95d.jsonl"
    iso: "2026-06-11"
---

# `openshell-containment` — 沙盒內因果鏈（technical-landing causal chain）

> CONTEXT「沙盒內因果鏈」義：該沙盒從外部概念 → 落地 → runtime-proven 的鏈。
> **與 `absorption-form.md`（吸收形式因果鏈）是兩份**（用戶明示，禁合併）。

## 鏈（外部概念 → 接口暴露）

| 階段 | 內容 | 證據（hard data，非自述） |
|------|------|--------------------------|
| **外部概念** | decouple-zero-trust DR 的 zero-trust thesis：agent-generated code 不可信，邊界必須 enforced（policy-governed sandbox），非靠 LLM 自願走 hook | bridge（DR core thesis；northstar 私有 skill 層，含內部安全架構 mirror，未隨附） |
| **bridge** | 把 thesis 變 northstar-shaped demand：不是「裝個 sandbox」（symptom）而是「**證明** policy-governed sandbox 真擋它宣稱擋的對抗路徑」（PG-167 meta-demand）。northstar 先前 = policy-by-cooperation（LLM 須自走的 hook） | bridge same_problem + missing_important；PG-101/PG-143 activation-gap |
| **build** | 落地真 NVIDIA OpenShell（v0.0.59 alpha）為 Runtime-containment 層：`src/sandbox_runner.py`（thin `openshell sandbox exec` wrapper，loosely-coupled 可換 primitive）+ `src/openshell_gateway_bootstrap.sh`（macOS 9-layer same-path keystone fix：gateway 容器 HOME=host-home + same-path mount） | `src/sandbox_runner.py` · `src/openshell_gateway_bootstrap.sh`（從 northstar 私有 execution 層 git mv，零重寫） |
| **對抗驗證** | `src/containment_probe.py` 跑 3 確定性 case：legit /sandbox write 須 PASS；adversarial egress（非 allowlist host）須 BLOCK（curl 56 / 403）；adversarial /Users host-home 須 NOT visible。count_metric=失敗數，0=fully contained。placebo-guard discrimination：permissive sandbox 不能 score 0（classifier pure function 雙向單元測） | trace：`data/production/containment/2026-06-11-containment-verdict.json` · 本 session live：3 cases / 0 failures（egress curl(56)/403, /Users no-such-file, /sandbox write ok）· exit 0 |
| **接口暴露** | `SKILL.md` 創建 `/openshell-containment` /command + `!`cmd`` 注入 gateway/sandbox/trace 當前狀態；flywheel 基於真實 runtime 狀態調用 | `SKILL.md`（C1-C5）+ `../PANORAMA.md` row |

## 誠實邊界（Slop #18）

- 本沙盒封裝的是**已 runtime-proven 的 containment 能力**（report-only 對抗驗證 + thin exec wrapper + bootstrap）。
- **不封裝**：auto-fix（containment_probe 是 report-only，surfaced gap 永遠交人，engine-locus 不破）；
  Linux 原生 driver（本 bootstrap 是 macOS Docker Desktop sibling-container 的 same-path workaround，Linux 不需此 9 層）。
- **runtime efficacy 是 LIVE 條件，非永真**：gateway 非 perennial-up（Docker daemon 依賴）。gateway down →
  containment_probe self-fail-loud exit 1（precondition env-fail），沙盒落 WIRED 而非偽綠（誠實記錄）。
