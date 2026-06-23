---
name: self-correcting-loop
description: >
  Deterministic DECIDE gate for a PLAN/DO/VERIFY/DECIDE self-correcting loop — the LLM produces and
  scores an artifact against a rubric each round, and this kernel mechanically decides FINAL (every
  criterion score >= its threshold) vs ITERATING (returns the weakest failing criterion as the next
  focus), plus a bounded no-progress / exhaustion guard. So "FINAL" is entailed by real scores, never
  an agent's prose claim (deterministic, no LLM-judge). 觸發詞（triggers）: self-correcting-loop, 自我修正迴圈,
  rubric-gate, plan-do-verify-decide, 迭代收斂.
allowed-tools: Bash(python3 sandboxes/self-correcting-loop/src/loop_kernel.py:*), Bash(python3 --version)
triggers: [self-correcting-loop, 自我修正迴圈, rubric-gate, plan-do-verify-decide, 迭代收斂]
---

# /self-correcting-loop — deterministic DECIDE gate for a self-correcting refinement loop

> 接口契約文件：本 SKILL.md 是這個沙盒的接口契約，受沙盒的驗證 gate 機械驗
> （`sandboxes/` 非 skill root，故不被動載入；可調用入口 = `.claude/commands/self-correcting-loop.md`）。
> 用 `!`cmd`` dynamic context injection 把當前 loop 狀態即時注入 context。
> 分工原則：kernel 只做確定性 **DECIDE**（FINAL/ITERATING + 最弱項）；PLAN/DO/VERIFY（產出與
> 評分）= LLM；**target + rubric 由人提供、FINAL 結果由人接受**——本接口不自動接受結果（一個人接受最終結果）。

## 啟動前置（C5 / 啟動方式；fail-loud — 前置不滿足顯式錯誤，禁靜默偽完成）

kernel 是純 python，無外部依賴。invocation-time 注入真狀態：

- 前置檢查（python present → exit 0）: !`python3 --version`

> ☝ 若缺 python（上方無版本輸出）→ 顯式報錯，**禁**偽造 DECIDE 結果（fail-loud）。

## 沙盒當前 runtime 狀態（C2 — MUST，≥1 個 live-state 注入）

注入當前 loop-state 快照（迭代數 / 上輪 scorecard / 最弱項 / FINAL·ITERATING / 無進展守衛）的真 stdout
——讓下一輪 PLAN 基於真實狀態而非過時猜測聚焦最弱項：

```!
timeout 5 python3 sandboxes/self-correcting-loop/src/loop_kernel.py state --loop default 2>&1 || echo "[no-loop-state exit=$?]"
```

> ⚠ C2 硬要求：上面注入的是**當前 loop runtime 狀態**（真 stdout），非靜態文字。
> 首次調用尚無 state → 顯示 `[no-loop-state: default]`（正常，第一輪 DO 後即有）。

## 能力與調用（沙盒做什麼）

`/self-correcting-loop` 被調用時驅動一輪有界自我修正迴圈（src seam = `src/loop_kernel.py`）：

1. **PLAN**（LLM）：讀注入的 loop-state，鎖定上輪最弱項（`focus`）作為本輪修復重點。
2. **DO**（LLM）：產出 / 改良 artifact。
3. **VERIFY**（LLM）：對 rubric 每條 criterion 給 1-10 分，寫成 scorecard JSON。
4. **DECIDE**（kernel，確定性）：`python3 src/loop_kernel.py decide --rubric R.json --scorecard S.json --loop NAME --iso ISO`
   → `FINAL`(exit 0) iff 每條 ≥ threshold；否則 `ITERATING`(exit 3) + 最弱失敗項；同時 advance loop-state。
   no-progress（min_score 連續 N 輪不升）或 exhausted（達 max_iterations 未 FINAL）→ **SURFACE 交人**，不自動續跑。

bundled fixtures（`src/fixtures/`）= 用戶範例 rubric（professional / readability / layout，threshold 8）供
`selftest` 自驗。底層 seam `src/loop_kernel.py` 是純函數 kernel（無 Ollama / 無網路 / 無 datetime.now）。

## 誠實邊界（硬約束）

本沙盒**只**機械化迴圈的 **DECIDE** 半（rubric 閘 + 收斂追蹤），**明確未封裝**：
- **PLAN / DO / VERIFY** = LLM 職責（評分本身仍是 LLM 判斷；kernel 只裁 score 是否達標，**不**代評分）。
- **指標迭代於程式碼** = autoresearch 的事（本 kernel 是 artifact-to-rubric 泛型，非 code-metric 引擎）。
- **重構迴圈** = `/refactor-loop`（7 槽 recipe 已有既有實現）。
  本 kernel 唯一新增 = 確定性 DECIDE 閘 + 有界守衛——組合既有的 loop 層（autoresearch / refactor-loop），不造新引擎。

## 全景圖註冊

本沙盒在 [`../PANORAMA.md`](../PANORAMA.md) 有對應 ```yaml sandbox``` block（沙盒的驗證 gate 機械查）。
