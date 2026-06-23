# `self-correcting-loop` — 沙盒內因果鏈（technical-landing causal chain）

> CONTEXT「沙盒內因果鏈」義：該沙盒從外部概念 → 落地 → runtime-proven 的鏈。
> **與 `absorption-form.md`（吸收形式因果鏈）是兩份**（用戶明示，禁合併）。

## 鏈（外部概念 → 接口暴露）

| 階段 | 內容 | 證據（hard data，非自述） |
|------|------|--------------------------|
| **外部概念** | 用戶給的「自我修正迴圈」協定：PLAN/DO/VERIFY/DECIDE 反覆，直到每條成功標準 ≥ 8 分才判 FINAL，否則 ITERATING 並優先修最低分項。同形於 autoresearch 的有界迭代契約（modify→verify→keep/discard against a metric）。 | 用戶 cc-20260623 prompt（task 描述：ZKP 科普文 rubric 範例 + 迴圈協定四步） |
| **bridge** | same-problem = 有界自我修正迭代；differential = 把 **DECIDE** 從「LLM 自評自判 FINAL」抽成**確定性閘**（FINAL iff 真實分數 ≥ threshold），治 PG-102 幻覺傳播 / PG-009「結構過了行為沒過」。cohere-not-build：autoresearch=code-metric 實例、/refactor-loop=重構實例，本沙盒=artifact-to-rubric 泛型實例。 | skill_match 重疊 hard data（adlc 2.8 / autoresearch-composer 1.2）→ 裁定 compose 既有層，唯一新增 = 確定性 DECIDE 閘 |
| **build** | `src/loop_kernel.py` 純函數 kernel：`decide(rubric, scorecard)`（FINAL/ITERATING + 最弱失敗項，tie-break = 低分優先再 declared order）+ `advance()` 有界 loop-state（no-progress plateau + max-iteration exhaustion SURFACE 守衛）+ fail-loud `validate_scorecard`/`load_rubric`。零 Ollama / 零網路 / 零 datetime.now（唯一時戳源 = 顯式 iso 參數）。 | `sandboxes/self-correcting-loop/src/loop_kernel.py`（本 commit） |
| **對抗驗證** | (1) `selftest` runtime exit 0（decide FINAL / ITERATING+focus / 兩條 fail-loud 全綠）；(2) pytest 25 tests 覆蓋每分支，含 tie-break、no-progress plateau、exhaustion、bool-score 不被當 int、unknown-criterion fail-loud；(3) `fold_in_sandbox_gate` 三層全綠。 | trace `trace/2026-06-23-selftest.json`（ok=true）+ pytest 25 passed + fold-in-gate record（runtime tier exit 0） |
| **接口暴露** | `.claude/commands/self-correcting-loop.md`（command-only 入口，避被動上下文）+ 本 SKILL.md C2 注入 loop-state 快照。adlc S1 loop registry 第 5 row + S3 DCI 5 條契約 + loop-ledger 雙檔。 | `.claude/commands/self-correcting-loop.md` + `../PANORAMA.md` block + `.claude/skills/adlc/skill.md` S1 row |

## 誠實邊界（Slop #18）

本沙盒只封裝**真正 landed** 的能力半 = 確定性 **DECIDE 閘 + 有界守衛**。明確**沒**落地：
- **PLAN / DO / VERIFY**（含每條 criterion 的評分本身）仍是 LLM 職責——kernel 不代評分，只裁分數是否達標。
- autoresearch 的 code-metric 迭代引擎、/refactor-loop 的 7 槽 recipe = declined（已有 owner，不重造）。
- 評分的「事實真假」（VERIFY 給的分對不對）= method-dependent，無機器閘強制（同 northstar external-verify 的結構面 vs 事實面分界）。kernel 只保證 FINAL **機械蘊含於所宣稱的分數**，不保證分數本身誠實。
