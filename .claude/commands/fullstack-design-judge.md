---
name: fullstack-design-judge
description: "對一個分散式前後端 + BFF + AI-Agent 異步系統的設計或代碼，按 DR 蒸餾的 rubric（10 軸 × macro 架構 / micro 代碼）跑一輪 PLAN/DO/VERIFY/DECIDE 自我修正迴圈，當 loop 的 Judge/evals 標準引導宏觀系統架構 → 微觀代碼實現。DECIDE 委派 self-correcting-loop 沙盒的確定性 kernel（FINAL iff ∀criterion ≥ threshold；runnable 軸零 LLM exit code，deterministic (no LLM-judge)）。Use when: 評判 BFF/前後端/Agent-async 系統設計、要把 DR 完整概念當 Judge 標準餵迴圈、引導架構+代碼方向。NOT for: 自動改代碼/自動接受 FINAL（report-only boundary 紅線：人 admit + SURFACE）、通用 Clean-Arch 結構適應度（/arch-fitness）、per-function 複雜度迭代（/refactor-loop）、建新沙盒。"
argument-hint: "[--tier macro|micro|combined] [--loop <name>=default] [--iso <ISO>] [--target <design-or-repo>]"
allowed-tools: Bash(timeout 5 python3 sandboxes/self-correcting-loop/src/loop_kernel.py:*), Bash(python3 sandboxes/self-correcting-loop/src/loop_kernel.py:*), Bash(python3 sandboxes/fullstack-design-judge/src/scorecard_template.py:*), Bash(python3 sandboxes/fullstack-design-judge/src/judge_selftest.py:*), Bash(python3 --version), Bash(echo:*)
# L2 attestation (loop-cooperation-spec L2 + adlc S3 DCI 5-rule): 1 intended DCI injection (judge loop state, L21),
# timeout-wrapped + bounded (state snapshot ≤~12 lines by construction) + placeholder ABORT (invariants) +
# exit-mask-handled (|| echo "[no-judge-loop-state exit=$?]"). L3 tier = in-session /loop (Tier-1). first-flight:
# WIRED until one organic /fullstack-design-judge fire (cac-trace), per the issue discipline. .
activation_injection: true
---

# /fullstack-design-judge — 分散式前後端設計 Judge/evals 標準（引導宏觀架構 + 微觀代碼）

## 描述
薄層 command（同 /self-correcting-loop / /arch-fitness 形，**零新引擎**）：對一個分散式前後端 + BFF +
Agent-async 系統的設計或代碼，用 DR 蒸餾的 rubric（`sandboxes/fullstack-design-judge/recipes/`）跑一輪
PLAN/DO/VERIFY/DECIDE，**DECIDE 步委派 self-correcting-loop 沙盒的確定性 kernel**
（`sandboxes/self-correcting-loop/src/loop_kernel.py`，本檔指向不複述；`requires: [self-correcting-loop]`）。
kernel 機械裁 FINAL/ITERATING，使「FINAL」蘊含於真實分數而非 agent 自評（deterministic (no LLM-judge)）。

## 實時沙盒狀態（Dynamic Context Injection — 啟動瞬間快照，非過時猜測）

### default judge-loop 當前狀態（bounded：state 快照按構造 ≤~12 行；無 state 時顯式 sentinel）
!`timeout 5 python3 sandboxes/self-correcting-loop/src/loop_kernel.py state --loop default --state-dir sandboxes/fullstack-design-judge/state 2>&1 || echo "[no-judge-loop-state exit=$?]"`

## 不變量（違反即停）
- **fail-loud on disabled policy**：若上方注入內容是字面 `[shell command execution disabled by policy]`
  → **立即 ABORT**，指示：「injection 被 `disableSkillShellExecution` 全域停用；請從 settings 移除該 key
  後重跑，或手動執行 `python3 sandboxes/self-correcting-loop/src/loop_kernel.py state --loop <name> --state-dir sandboxes/fullstack-design-judge/state`」。
  **永不**在無實時狀態下靜默續行（過時猜測 = 本接口存在的反命題）。
- **紅線 report-only boundary（the issue / loop-cooperation L5）**：本 command 只**驅動迭代 + 注入狀態 + 當 Judge 標準 + 裁 DECIDE**。
  **被判 artifact + rubric 由人 admit；改不改設計/代碼、FINAL 接不接受由人/loop DECIDE 裁**。
  kernel 回 `no_progress` / `exhausted` = **SURFACE 交人**（report-only），**永不**自動改 artifact、**永不** 自動裁定 自動續跑。
- **不代評分（不偽判語義）**：VERIFY 每條 criterion 分數由 LLM/人出——runnable 軸跑**真**行為檢查取 exit code、
  rubric 軸 LLM 評 1-10；kernel 只裁分數是否達標，不代生成分數。把語義偽裝成機器 verdict = placebo-fitness（the issue）。
- **fail-loud 不吞 exit**：注入失敗分支顯式 `|| echo "[no-judge-loop-state exit=$?]"`；
  禁 `| tail` / `| head` 吞 exit（a known bug-scar / bash_exit_mask_guard）。

## 參數
- `$ARGUMENTS`:
  - `--tier macro|micro|combined`：用哪份 rubric。**預設兩層流**：先 `macro`（收斂宏觀架構）→ 再 `micro`
    （收斂微觀代碼）；`combined` = 21 條單次全合規。rubric 在 `recipes/fullstack-design.<tier>.rubric.json`。
  - `--loop <name>`：loop 實例名（default `default`）；state 落 `sandboxes/fullstack-design-judge/state/<name>.json`。
  - `--iso <ISO>`：本輪時戳（determinism；caller 供）。
  - `--target <design-or-repo>`：被判的設計文件或源碼樹（人 admit）。

## 執行步驟（迴圈協定 — 一輪 = 一次調用）
1. **讀注入**：上方 default judge-loop 狀態。含 placeholder → 依不變量 ABORT。顯 `[no-judge-loop-state ...]` = 第一輪。
2. **PLAN**：選 tier（預設先 `macro`）。若有上輪 state，鎖定 `focus`（最弱失敗軸）為本輪修復重點；否則據該 tier rubric 規劃首版。
   ⚠ 若注入顯示 `NO-PROGRESS` 或 `EXHAUSTED` → **停下 SURFACE 交人**，不自動再迭代。
3. **DO**：改良 target（`macro` 改設計 / `micro` 改代碼）朝 step-2 focus。**本 command 不改 artifact**（report-only boundary）——人/agent 改。
4. **VERIFY**：先產 scorecard skeleton（保證 keys == rubric ids，避 exact-match footgun）：
   `python3 sandboxes/fullstack-design-judge/src/scorecard_template.py --rubric recipes/fullstack-design.<tier>.rubric.json > scorecard.json`
   再填值——**runnable 軸**：對 `--target` 跑真行為檢查（如負值繞 UI 直打 API → 4xx；解析 Set-Cookie 四屬性；
   N 並發無雙扣；跑測試套件）取其 **exit code**；**rubric 軸**：LLM 對 criterion 描述誠實評 1-10。
5. **DECIDE（確定性）**：
   `python3 sandboxes/self-correcting-loop/src/loop_kernel.py decide --rubric recipes/fullstack-design.<tier>.rubric.json --scorecard scorecard.json --loop <name> --iso <ISO> --state-dir sandboxes/fullstack-design-judge/state; echo EXIT=$?`
   - `EXIT=0` = **FINAL**（∀criterion 達標）→ 印 FINAL + scorecard；若剛收斂 `macro` → 提示切 `--tier micro` 收斂代碼；macro∧micro 皆 FINAL = 整體達標，向人回報，**終止**。
   - `EXIT=3` = **ITERATING** → 讀輸出的 `focus`（最弱軸，runnable 失敗硬阻斷優先），回步驟 2 下一輪（同一 `--loop` 累積 state）。
   - `EXIT=1` = 輸入錯誤（rubric/scorecard 不合法，如 FILL placeholder 未填）→ fail-loud，修輸入重跑，不偽造判定。
6. **收尾**：FINAL 時回報——tier、迭代數、各 criterion 終分、loop-state 路徑、下一 tier 提示；ITERATING 時回報 focus + 續跑。

## 路由
- rubric/recipe owner（全景圖）= `sandboxes/fullstack-design-judge/`（PANORAMA `fullstack-design-judge` block，wiring 見該 block）。
- DECIDE kernel = `sandboxes/self-correcting-loop/`（composed，`requires:`；不複述）。
- **配合 loop 的可重跑 recipe**（turnkey 指令 + 兩層流 + exact-match 契約）→ [`sandboxes/fullstack-design-judge/recipes/with-self-correcting-loop.md`](../../sandboxes/fullstack-design-judge/recipes/with-self-correcting-loop.md)。
- loop 治理（何時起此 loop · WHAT 誰定 · DCI 注入面）= `.claude/skills/adlc/skill.md` S1/S3 + loop-cooperation-spec L1-L6。
- 平行 loop（不同軸，互補）：通用 Clean-Arch 結構適應度 → `/arch-fitness`（sibling，同 compose self-correcting-loop）；per-function 複雜度迭代 → `/refactor-loop`；架構 deepening/consolidation → `/improve-codebase-architecture`。
