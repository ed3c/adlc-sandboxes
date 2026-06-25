---
name: capacity-estimation
description: "AI-Agent 容量估算 + 可行性 rubric judge（DR『AI Agent 時代計算系統容量估算與架構設計』完整框架的確定性編碼）。給定 agent 系統 spec → 算 DR 五步指標（Agent QPS / Token TPS / 顯存權重+KV / 前綴快取 breakeven / RAG RAM）→ judge FEASIBLE(exit 0)/INFEASIBLE(exit 3) + 綁定約束 + DR 宏觀架構槓桿(卡數/TP/RAM) 與微觀代碼槓桿(PagedAttention/FP8/RadixAttention/SQ8/DiskANN)。judge exit 0/3 可作 /self-correcting-loop 的 runnable criterion = 迴圈工程的確定性 Judge/evals 軸。Use when: 估算/裁定一個 AI Agent 系統的算力容量、顯存併發、Token 吞吐、RAG RAM 是否可行、要買幾張卡開哪些優化。NOT for: 真跑 vLLM/SGLang 量測、架構決策本身(人 admit)、自動裁定 自動接受裁定(report-only boundary 紅線)。"
argument-hint: "[--spec <path>] [--budgets <path>] [--loop <name>=default] [--iso <ISO>]"
allowed-tools: Bash(timeout 5 python3 sandboxes/capacity-estimation/src/capacity_kernel.py:*), Bash(python3 sandboxes/capacity-estimation/src/capacity_kernel.py:*), Bash(python3 --version), Bash(echo:*)
# L2 attestation (adlc S3 DCI 5-rule): 1 intended DCI injection (state snapshot) — timeout-wrapped +
# bounded (<=~10 lines by construction) + placeholder ABORT (invariants) + exit-mask-handled
# (|| echo "[no-loop-state exit=$?]"). first-flight: WIRED until one organic /capacity-estimation fire
# (cac-trace), per the issue discipline. .
activation_injection: true
---

# /capacity-estimation — AI-Agent 容量估算 + 可行性 rubric judge (確定性，DR 完整框架編碼)

## 描述
薄層 command（同 /self-correcting-loop 形，零新引擎）：把 DR「AI Agent 時代計算系統容量估算與架構設計」的
§5 五步檢核表機械化成一個**確定性估算器 + 可行性 judge**，委派 `capacity-estimation` 沙盒的純函數 kernel
（`sandboxes/capacity-estimation/src/capacity_kernel.py`，本檔指向不複述）。kernel 機械裁
FEASIBLE/INFEASIBLE，使「可行」蘊含於真實數字 vs 預算而非 agent 自評（deterministic (no LLM-judge)）。

## 實時 capacity-loop 狀態（Dynamic Context Injection — 啟動瞬間快照，非過時猜測）

### default loop 當前狀態（bounded：state 快照按構造 ≤~10 行；無 state 時顯式 sentinel）
!`timeout 5 python3 sandboxes/capacity-estimation/src/capacity_kernel.py state --loop default 2>&1 || echo "[no-loop-state exit=$?]"`

## 不變量（違反即停）
- **fail-loud on disabled policy**：若上方注入內容是字面 `[shell command execution disabled by policy]`
  → **立即 ABORT**，指示：「injection 被 `disableSkillShellExecution` 全域停用；請從 settings 移除該 key
  後重跑，或手動執行 `python3 sandboxes/capacity-estimation/src/capacity_kernel.py state --loop <名>`」。
  **永不**在無實時狀態下靜默續行（過時猜測 = 本接口存在的反命題）。
- **紅線 report-only boundary（the issue）**：本 command 只**算估算 + 裁可行性 + 注入狀態**。
  **spec + budgets 由人 admit；FEASIBLE/INFEASIBLE 結果與架構決策（買卡/開 FP8/切 DiskANN）由人接受**。
  kernel **永不** 自動裁定 / 自動採購 / 自動改架構。
- **不偽造數字**：估算與裁定全由 kernel 的確定性公式出；缺 python 或 spec 不合法 → fail-loud，不憑記憶捏數字。
- **fail-loud 不吞 exit**：注入失敗分支顯式 `|| echo "[no-loop-state exit=$?]"`；
  禁 `| tail` / `| head` 吞 exit（a known bug-scar / bash_exit_mask_guard）。
- **DR 範例非真值**：DR 的併發 32 / context 4K 等是 illustrative；以使用者 spec 的真實參數估算，別把 DR 範例當定論。

## 參數
- `$ARGUMENTS`:
  - `--spec <path>`：agent 系統 spec JSON（workload / model / serving / rag / prefix_cache；schema 見 `src/fixtures/dr-example-spec.json`）
  - `--budgets <path>`：預算 JSON（cards_available / backend_rpm_limit / tpm_budget / host_ram_gb；省略則各 criterion 標 not_constrained 資訊性）
  - `--loop <name>`：capacity-loop 實例名（default `default`）；state 落 `sandboxes/capacity-estimation/state/<name>.json`
  - `--iso <ISO>`：本輪時戳（determinism；caller 供）

## 執行步驟（一次調用 = 一輪估算+裁定）
1. **讀注入**：上方 default loop 狀態。含 policy placeholder → 依不變量 ABORT。顯 `[no-loop-state ...]` = 首輪。
2. **estimate（確定性）**：`python3 sandboxes/capacity-estimation/src/capacity_kernel.py estimate --spec <SPEC>`
   → 讀 DR 五步指標數字（Agent QPS / Input·Output TPS / 權重+KV 顯存 GiB·GB / 前綴 breakeven / RAG RAM）。
3. **judge（確定性 rubric）**：
   `python3 sandboxes/capacity-estimation/src/capacity_kernel.py judge --spec <SPEC> --budgets <BUDGETS> --loop <名> --iso <ISO>; echo EXIT=$?`
   - `EXIT=0` = **FEASIBLE** → 向人回報五指標 + 各 criterion 在預算內，**終止**。
   - `EXIT=3` = **INFEASIBLE** → 讀輸出 `binding` 綁定約束清單，每條帶 DR `lever.macro`(宏觀架構) + `lever.micro`(微觀代碼)；
     把這兩尺度方向 SURFACE 給人，由人 admit 下一步架構/代碼調整後再跑下一輪（同 `--loop` 名累積 state）。
   - `EXIT=1` = 輸入錯誤（spec/budgets 不合法）→ fail-loud，修輸入重跑，不偽造判定。
4. **收尾**：FEASIBLE 時回報五指標終值 + loop-state 路徑；INFEASIBLE 時回報綁定約束 + 宏觀/微觀槓桿選項交人。

## 配合迴圈工程（核心組合用法）
judge exit 0/3 與 `/self-correcting-loop` 的 DECIDE FINAL/ITERATING 同語意 → 把
`python3 sandboxes/capacity-estimation/src/capacity_kernel.py judge --spec <SPEC> --budgets <B>` 設為
`/self-correcting-loop` rubric 的一條 `kind: runnable` criterion，即可讓「capacity-feasible」成為迴圈工程的
**確定性 Judge/evals 軸**，每輪把 agent 系統架構迭代同時導向宏觀 sizing 與微觀代碼優化。

## 路由
- 容量估算 kernel owner（全景圖）= `sandboxes/capacity-estimation/`（PANORAMA `capacity-estimation` block）。
- DR 公式溯源 = `sandboxes/capacity-estimation/docs/dr-formula-inventory.md`（49 圖轉錄 + 5 步檢核表）。
- loop 治理（何時起 · WHAT 誰定 · DCI 注入面 · 因果鏈帳本）= `.claude/skills/adlc/skill.md` S1/S3。
- 平行 loop：通用 artifact-to-rubric 自我修正 → `/self-correcting-loop`（本 command 提供其領域 capacity 判據）。
