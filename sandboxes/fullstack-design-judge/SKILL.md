---
name: fullstack-design-judge
description: >
  Judge a distributed 前後端 + BFF + AI-Agent 異步任務調度 system DESIGN or CODE against a DR-distilled
  rubric (10 axes x macro 架構 / micro 代碼), used as a loop-engineering Judge/evals standard to guide
  宏觀系統架構 down to 微觀代碼實現. DECIDE is delegated to the self-correcting-loop kernel (FINAL iff every
  criterion >= threshold; runnable axes are zero-LLM exit-code checks). 觸發詞（triggers）:
  fullstack-design-judge, 分散式設計評判, BFF設計評判, 前後端架構評判, 系統設計rubric, design-judge.
allowed-tools: Bash(timeout 5 python3 sandboxes/self-correcting-loop/src/loop_kernel.py:*), Bash(python3 sandboxes/self-correcting-loop/src/loop_kernel.py:*), Bash(python3 sandboxes/fullstack-design-judge/src/judge_selftest.py:*), Bash(python3 --version), Bash(echo:*)
triggers: [fullstack-design-judge, 分散式設計評判, BFF設計評判, 前後端架構評判, 系統設計rubric, design-judge]
---

# fullstack-design-judge — DR-distilled fullstack-design Judge rubric over the self-correcting-loop kernel

> 沙盒接口契約文件：本 SKILL.md 是這個沙盒的接口契約，受沙盒的驗證 gate 機械驗
> （`sandboxes/` 非 skill root，故不被動載入；直接以下方 `judge_selftest.py` / loop kernel 調用）。
> **零新引擎**：本沙盒只新增「DR 蒸餾的領域 rubric」（10 軸 × macro/micro），
> **DECIDE 復用 `self-correcting-loop` 沙盒的確定性 kernel**（`requires: [self-correcting-loop]`，
> runtime trace 印 `CONSUMED:self-correcting-loop` 供 composition tier 機械驗）。
> 分工原則：kernel 只做確定性 DECIDE；PLAN/DO/VERIFY（含每條 criterion 評分）= LLM；
> **被判 artifact + rubric 由人提供、FINAL 結果由人接受**——不自動接受結果（一個人接受最終結果）。

## 啟動前置（C5 / fail-loud — 前置不滿足顯式錯誤，禁靜默偽完成）

kernel 是純 python（復用 self-correcting-loop），無外部依賴。invocation-time 注入真狀態：

- 前置檢查（python present → exit 0）: !`python3 --version`

> ☝ 若缺 python（上方無版本輸出）→ 顯式報錯，**禁**偽造 DECIDE 結果（fail-loud）。
> 若復用的 kernel `sandboxes/self-correcting-loop/src/loop_kernel.py` 不存在 → 依賴未滿足，顯式報錯
> （本沙盒 compose 它、不重造；runtime tier 的 `judge_selftest.py` 對此 fail-loud）。

## 沙盒當前 runtime 狀態（C2 — MUST，≥1 個 live-state 注入）

注入當前 design-judge loop-state 快照（迭代數 / 上輪 scorecard / 最弱項 / FINAL·ITERATING / 無進展守衛）
的真 stdout——讓下一輪 PLAN 基於真實狀態而非過時猜測聚焦最弱的架構/代碼軸：

```!
timeout 5 python3 sandboxes/self-correcting-loop/src/loop_kernel.py state --loop default --state-dir sandboxes/fullstack-design-judge/state 2>&1 || echo "[no-judge-loop-state exit=$?]"
```

> ⚠ C2 硬要求：上面注入的是**當前 loop runtime 狀態**（真 stdout），非靜態文字。
> 首次調用尚無 state → 顯示 `[no-loop-state: default]`（正常，第一輪 DECIDE 後即有）。

## 能力與調用（沙盒做什麼）

本沙盒把一個**分散式前後端 + BFF + Agent 異步系統**的設計或代碼，按 DR 蒸餾的 rubric 跑一輪
PLAN/DO/VERIFY/DECIDE 自我修正迴圈，**引導宏觀架構→微觀代碼**：

1. **rubric 源**（`recipes/`，本沙盒唯一新增實體）：
   - `fullstack-design.macro.rubric.json` — 10 條宏觀架構 criterion（零信任邊界 / 契約先行 SSOT /
     SoC 四步驟 / 併發控制 / BFF 聚合層 / BFF-Gateway 分野 / BFF-OAuth 拓撲 / 異步解耦 / 協議取捨 /
     並行扇出），全 `kind:rubric`（架構判斷語義）。
   - `fullstack-design.micro.rubric.json` — 11 條微觀代碼 criterion，**mix**：可機械查的（負值拒絕 /
     共享 schema 無重複 / 契約測試 / 原子併發 / idempotency / Cookie 四屬性 / tests-pass）= `kind:runnable`
     （零 LLM，exit code）；不可化約語義的（前端不持權威計算 / 並行非串行 / 串流韌性 / 任務可觀測）= `kind:rubric`。
   - `fullstack-design.rubric.json` — 合併（21 條，單次全判）。
2. **兩層流（引導方向）**：先用 `.macro.` 收斂**宏觀架構**（FINAL = 每條架構軸達標），再用 `.micro.`
   收斂**微觀代碼**；或用合併 rubric 做最終全合規檢查。
3. **DECIDE（確定性，復用 kernel）**：`python3 sandboxes/self-correcting-loop/src/loop_kernel.py decide
   --rubric <R> --scorecard <S> --loop <name> --iso <ISO> --state-dir sandboxes/fullstack-design-judge/state`
   → `FINAL`(exit 0) iff 每條 ≥ threshold（runnable = exit 0）；否則 `ITERATING`(exit 3) + 最弱失敗軸（focus）。
   no-progress / exhausted → **SURFACE 交人**，不自動續跑。

`src/judge_selftest.py`（runtime trace）= 證明：跑 kernel 對三份 rubric（FINAL + ITERATING +
runnable-priority），印 `CONSUMED:self-correcting-loop`，並機械驗 `combined == macro ∪ micro`（防漂移）。

## 誠實邊界（硬約束）

本沙盒**誠實是 `self-correcting-loop` 的薄 domain delta**（如 sandcastle 之於 openshell）：
- **DECIDE 迴圈引擎 = 復用，未重造**（`requires: [self-correcting-loop]`；造第二個 decider = 抽象膨脹）。
- **唯一新增 = DR 蒸餾的領域 rubric**（criteria + thresholds + runnable/rubric kind 切分），這是真正的智力產物。
- **評分的事實真假** = LLM/人 VERIFY 職責；kernel 只裁分數是否達標、不代評分。kernel 保證 FINAL 機械蘊含於
  所宣稱分數，不保證分數本身誠實。
- **runnable criterion 需真 artifact 的代碼/測試**才能跑出真 exit code；對純設計文件（無代碼）用 `.macro.`
  rubric（純 `kind:rubric`），不要對沒有代碼的東西宣稱 runnable 軸 pass。
- **opinionated 主張寫成條件式**（external-verified）：協議「SSE 最優」、扇出「60-70%」不是絕對對錯，
  rubric 已改成「選 X 須處理代價 Y / claim 須精確」（錨 RFC/IETF/OWASP）。

## 全景圖註冊

本沙盒在 [`../PANORAMA.md`](../PANORAMA.md) 有對應 ```yaml sandbox``` block（沙盒的驗證 gate 機械查）。
