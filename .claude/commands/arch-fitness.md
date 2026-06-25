---
name: arch-fitness
description: "對一個 target 源碼樹跑確定性『架構適應度 Judge/evals 標準』——量測模型-代碼縫隙：Clean-Arch 分層依賴違規 + 模組化單體 module-boundary 違規 + Martin I/A/D 耦合(痛苦區) + AST 壞味道(Long Method/Too Many Params/Large Class)，verdict PASS iff 0 hard 違規 + focus 導引方向(deterministic (no LLM-judge) 零 LLM-judge)。配合迴圈工程當 Judge/evals 標準(rubric=DR 完整概念 macro/micro/governance；scorecard 投影給 /self-correcting-loop)，引導宏觀架構與微觀代碼。Use when: 量架構適應度、抓架構侵蝁/模型-代碼縫隙、要架構 evals 標準餵 loop。NOT for: 自動改代碼(report-only boundary 紅線：surface 交人/loop)、per-function 複雜度迭代(/refactor-loop)、自動裁定 自動接受(report-only boundary)。"
argument-hint: "[--target <repo-root>] [--spec <arch-model.yaml>] [--iso <ISO>] [--mode measure|rubric|scorecard]"
allowed-tools: Bash(timeout 5 python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py:*), Bash(python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py:*), Bash(python3 --version), Bash(echo:*)
# L2 attestation (loop-cooperation-spec L2 + adlc S3 DCI 5-rule): 1 intended DCI injection (status, L24),
# timeout-wrapped + bounded (status ≤~6 lines by construction) + placeholder ABORT (invariants) +
# exit-mask-handled (|| echo "[…exit=$?]"). L3 tier = in-session /loop (Tier-1). first-flight: WIRED until
# one organic /arch-fitness fire (cac-trace), per the issue discipline. .
activation_injection: true
---

# /arch-fitness — 架構適應度 Judge/evals 標準（確定性，引導宏觀架構 + 微觀代碼）

## 描述
薄層 command（同 /self-correcting-loop 形，零新引擎）：對一個 target 源碼樹委派 `arch-fitness` 沙盒的確定性
kernel（`sandboxes/arch-fitness/src/arch_fitness_kernel.py`，本檔指向不複述）。kernel 把 target(CODE) 對
arch-model spec(MODEL) 量測，divergence = 模型-代碼縫隙，machine fact。**verdict/focus 蘊含於真實量測而非 agent 自評**（deterministic (no LLM-judge)）。

## 實時沙盒狀態（Dynamic Context Injection — 啟動瞬間快照，非過時猜測）

### 最近一次量測狀態（bounded：status 快照按構造 ≤~6 行；無量測時顯式 sentinel）
!`timeout 5 python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py status 2>&1 || echo "[arch-fitness status unavailable exit=$?]"`

## 不變量（違反即停）
- **fail-loud on disabled policy**：若上方注入是字面 `[shell command execution disabled by policy]` → **立即 ABORT**，
  指示：「injection 被 `disableSkillShellExecution` 全域停用；請移除該 key 後重跑，或手動執行
  `python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py status`」。**永不**在無實時狀態下靜默續行。
- **紅線 report-only boundary（the issue / loop-cooperation L5）**：本 command 只**量測 + surface focus + 當 loop 的 Judge/evals 標準**。
  **target + arch-model spec 由人 admit；改不改代碼、接不接受結果由人/loop 的 DECIDE 裁**。kernel 回 focus =
  **SURFACE 交人/loop**（report-only），**永不**自動改 target 代碼、**永不** 自動裁定 自動接受。
- **不偽判語義**：semantic 概念（深模組品質 / DDD 邊界 / 註釋）**不由本 kernel 判**，交 loop 的 LLM-VERIFY；
  把語義偽裝成機器 verdict = placebo-fitness（the issue）。kernel 只判它**真量得到**的確定性維度。
- **fail-loud 不吞 exit**：注入失敗分支顯式 `|| echo "[…exit=$?]"`；禁 `| tail`/`| head` 吞 exit（a known bug-scar / bash_exit_mask_guard）。

## 參數
- `$ARGUMENTS`:
  - `--target <repo-root>`：要量測的源碼樹根（CODE）
  - `--spec <arch-model.yaml>`：架構模型 spec（MODEL：components / layer_rules / allowed_dependencies / thresholds）
  - `--iso <ISO>`：本次時戳（determinism；caller 供）
  - `--mode`：`measure`(default) / `rubric`(印完整概念 Judge/evals 標準) / `scorecard`(投影給 loop)

## 執行步驟（一輪 = 一次調用）
1. **讀注入**：上方最近量測狀態。含 `[…disabled by policy]` → 依不變量 ABORT。顯 `[no measurement yet …]` = 首次量測。
2. **measure（確定性）**：
   `python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py measure --target <T> --spec <S> --iso <ISO>; echo EXIT=$?`
   - `EXIT=0` = **PASS**（0 hard 違規）→ 報告 verdict + 各維度 + 痛苦區診斷。
   - `EXIT=2` = **FAIL**（layer/boundary 侵蝁）→ 讀 `focus`，**surface** 給人/loop（不自動修）。
   - `EXIT=1` = 輸入錯誤（spec 不合法）→ fail-loud，修 spec 重跑，不偽造 verdict。
3. **surface 引導方向（宏觀 + 微觀）**：把報告分兩軸呈現給人——
   - **宏觀（strategic）**: layer_dependency / module_boundary 違規清單（帶 file:lineno）+ coupling 痛苦區 component；
   - **微觀（tactical）**: long_method / too_many_params / large_class 清單（帶 file:lineno）；
   - **focus** = 最該先動的維度（hard 違規優先）→ 下一步方向。
4. **配合迴圈工程（Judge/evals 標準）**：要把架構適應度當 loop 的 evals 標準時——
   `python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py scorecard --report <trace/<iso>-measure.json>`
   投影成 `/self-correcting-loop` 的 runnable scorecard；配 `rubric`（DR 完整概念標準）餵 loop：loop 跑
   DO(改 codebase)→VERIFY(re-measure 確定性維度 + LLM 評 semantic 維度)→DECIDE(self-correcting-loop kernel 裁 FINAL/ITERATING)。
   **kernel 只供確定性那半；semantic 半（深模組/DDD/註釋）由 loop 的 LLM-VERIFY 評**，禁機器偽判。
5. **收尾**：報告 verdict + focus + 痛苦區 + 各違規 file:lineno；**SURFACE 交人/loop**，不自動改代碼、不自動接受。

## 路由
- 量測 kernel owner（全景圖）= `sandboxes/arch-fitness/`（PANORAMA `arch-fitness` block）。
- 完整概念 Judge/evals 標準 = `arch_fitness_kernel.py rubric`（macro/micro/governance · deterministic|semantic|governance）+ `the absorbed-form notes (withheld)` 逐概念帳本。
- loop 治理（何時起此 loop · WHAT 誰定 · DCI 注入面）= `.claude/skills/adlc/skill.md` S1/S3 + loop-cooperation-spec L1-L6。
- 平行 loop：rubric 閘判 FINAL → `/self-correcting-loop`；per-function 複雜度迭代 → `/refactor-loop`；架構 deepening/consolidation 找候選 → `/improve-codebase-architecture`。
- **配合 loop 的可重跑 recipe**（turnkey 指令 + rubric 範本）→ [`sandboxes/arch-fitness/recipes/with-self-correcting-loop.md`](../../sandboxes/arch-fitness/recipes/with-self-correcting-loop.md) + [`arch-fitness.rubric.json`](../../sandboxes/arch-fitness/recipes/arch-fitness.rubric.json)（`scorecard --dims` 讓 scorecard keys 精確匹配 rubric ids，零手術）。
