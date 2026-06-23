---
name: self-correcting-loop
description: "驅動一輪有界『自我修正迴圈』(PLAN/DO/VERIFY/DECIDE)，DECIDE 由 self-correcting-loop 沙盒的確定性 kernel 裁（FINAL iff ∀criterion ≥ threshold，否則 ITERATING + 最弱項），帶 no-progress / exhaustion 守衛。Use when: 要對某 artifact 按 rubric 反覆改良到達標、跑自我修正迴圈、rubric 閘判 FINAL。NOT for: code-metric 迭代（/autoresearch）、重構迴圈（/refactor-loop）、auto-DECISION 自動接受結果（engine-locus 紅線）。"
argument-hint: "[--loop <name>=default] [--rubric <path>] [--scorecard <path>] [--iso <ISO>] [--max <N>]"
allowed-tools: Bash(timeout 5 python3 sandboxes/self-correcting-loop/src/loop_kernel.py:*), Bash(python3 sandboxes/self-correcting-loop/src/loop_kernel.py:*), Bash(python3 --version), Bash(echo:*)
activation_injection: true
---

<!-- ════════════════════════════════════════════════════════════════════════
 MIRROR NOTE — 此檔從私有 northstar 的 `.claude/commands/self-correcting-loop.md` 鏡像而來，
 是 claude code **載入/驅動本沙盒的真實 `/command` 入口**（生產消費關係的消費端）。為公開展示，
 已清理「路由」段對 northstar 私有治理層（adlc skill / loop-ledger registry）的指向。
 sandboxes/self-correcting-loop/src/loop_kernel.py 在本 repo 即真實可跑（純 python3）。
 實際運作過程與真實輸出見同沙盒的 RUN.md。
 ════════════════════════════════════════════════════════════════════════ -->

# /self-correcting-loop — 有界自我修正迴圈驅動 (DECIDE 由確定性 kernel 裁)

## 描述
薄層 command（零新引擎）：驅動 PLAN/DO/VERIFY/DECIDE 一輪迭代，**DECIDE 步**委派 `self-correcting-loop`
沙盒的確定性 kernel（`sandboxes/self-correcting-loop/src/loop_kernel.py`，本檔指向不複述）。kernel 機械裁
FINAL/ITERATING，使「FINAL」蘊含於真實分數而非 agent 自評（DDR-031，零 LLM-judge）。

## 實時 loop 狀態（Dynamic Context Injection — 啟動瞬間快照，非過時猜測）

### default loop 當前狀態（bounded：state 快照按構造 ≤~12 行；無 state 時顯式 sentinel）
!`timeout 5 python3 sandboxes/self-correcting-loop/src/loop_kernel.py state --loop default 2>&1 || echo "[no-loop-state exit=$?]"`

## 不變量（違反即停）
- **fail-loud on disabled policy**：若上方注入內容是字面 `[shell command execution disabled by policy]`
  → **立即 ABORT**，指示：「injection 被 `disableSkillShellExecution` 全域停用；請從 settings 移除該 key
  後重跑，或手動執行 `python3 sandboxes/self-correcting-loop/src/loop_kernel.py state --loop <name>`」。
  **永不**在無實時狀態下靜默續行（過時猜測 = 本接口存在的反命題）。
- **紅線 engine-locus**：本 command 只**驅動迭代 + 注入狀態 + 裁 DECIDE**。
  **target + rubric 由人 admit；FINAL 結果由人接受**。kernel 回 `no_progress` / `exhausted` =
  **SURFACE 交人**（report-only），**永不** auto-DECISION / 自動無限續跑。
- **不代評分**：VERIFY 的每條 criterion 分數由 LLM/人出；kernel 只裁分數是否達 threshold，不代生成分數。
- **fail-loud 不吞 exit**：注入失敗分支顯式 `|| echo "[no-loop-state exit=$?]"`；
  禁 `| tail` / `| head` 吞 exit。

## 參數
- `$ARGUMENTS`:
  - `--loop <name>`：loop 實例名（default `default`）；state 落 `sandboxes/self-correcting-loop/state/<name>.json`
  - `--rubric <path>`：rubric JSON（criteria + 各 threshold；缺則沿用上輪或請人給）
  - `--scorecard <path>`：本輪 VERIFY 寫的 scorecard JSON（criterion_id: 1-10）
  - `--iso <ISO>`：本輪時戳（determinism；caller 供）
  - `--max <N>`：max_iterations（寫進 state；default 10）

## 執行步驟（迴圈協定 — 一輪 = 一次調用）
1. **讀注入**：上方 default loop 狀態。含 placeholder → 依不變量 ABORT。顯 `[no-loop-state ...]` = 第一輪。
2. **PLAN**：若有上輪 state，鎖定 `focus`（最弱失敗項）為本輪修復重點；否則據 rubric 規劃首版。
   ⚠ 若注入顯示 `NO-PROGRESS` 或 `EXHAUSTED` → **停下 SURFACE 交人**，不自動再迭代。
3. **DO**：產出 / 改良 artifact（聚焦步驟 2 的 focus）。
4. **VERIFY**：對 rubric 每條 criterion 誠實給 1-10 分，寫 scorecard JSON。
5. **DECIDE（確定性）**：
   `python3 sandboxes/self-correcting-loop/src/loop_kernel.py decide --rubric <R> --scorecard <S> --loop <name> --iso <ISO>; echo EXIT=$?`
   - `EXIT=0` = **FINAL**（∀criterion ≥ threshold）→ 印 FINAL，向人回報結果 + scorecard，**終止**。
   - `EXIT=3` = **ITERATING** → 讀輸出的 `focus`，回步驟 2 下一輪（同一 `--loop` 名累積 state）。
   - `EXIT=1` = 輸入錯誤（rubric/scorecard 不合法）→ fail-loud，修輸入重跑，不偽造判定。
6. **收尾**：FINAL 時回報——迭代數、各 criterion 終分、loop-state 路徑；ITERATING 時回報 focus + 續跑。

## 路由
- DECIDE kernel owner = `sandboxes/self-correcting-loop/`（[`../../sandboxes/PANORAMA.md`](../../sandboxes/PANORAMA.md) `self-correcting-loop` block，wiring LIVE）。
- 平行 loop：指標迭代於碼 → `/autoresearch`；重構迴圈 → `/refactor-loop`；本 command = artifact-to-rubric 泛型自我修正迴圈。
  （`/autoresearch` · `/refactor-loop` 是 northstar 私有的其他 command，**未隨附本鏡像**——此為已知 dangling reference。）
- loop 治理層（何時起此 loop · WHAT 誰定 · DCI 注入面 · 因果鏈帳本）= northstar 私有 `adlc` skill + loop-ledger registry，
  **刻意未隨附**（治理層留私有）。
