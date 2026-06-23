# `self-correcting-loop` — 吸收形式因果鏈（absorption-form causal chain）

> CONTEXT「吸收形式因果鏈」義：flywheel 從此沙盒**吸收了什麼形式**（C5 那套）。
> **與 `causal-chain.md`（沙盒內因果鏈）是兩份**（用戶明示，禁合併）。

## flywheel 吸收的形式

| 形式維度 | 本沙盒吸收進 flywheel 的形式 | join 點 |
|----------|------------------------------|---------|
| **pruning verdicts** | adopted = 確定性 DECIDE 閘（FINAL iff ∀ criterion ≥ threshold）+ 有界 loop 守衛（no-progress / exhaustion）。declined = code-metric 迭代引擎（autoresearch 已有）、重構迴圈 recipe（/refactor-loop 已有）、LLM 代評分（紅線：評分仍人/LLM 出，kernel 不代）。 | PANORAMA `self-correcting-loop` block · adlc S1 row |
| **cut_class** | adopted-only：唯一新增實體 = DECIDE 閘 kernel；其餘迴圈基礎設施 = narrowed（指向既有 autoresearch / refactor-loop / adlc，不複製）。 | adlc S1 「委派引擎」欄 |
| **runtime_comparison** | 硬數據差異 = **agent-judged DECIDE vs 確定性 DECIDE**：前者「全部 8 分所以 FINAL」可在分數未達標時假判 FINAL（PG-102/PG-009）；後者 `selftest` 證 `decide(rubric, scorecard-iterating)` 必回 ITERATING+focus，FINAL 機械蘊含於真實分數。 | trace `trace/2026-06-23-selftest.json`（reverse case：iterating fixture → ITERATING，非 FINAL） |

## 整合區更高階形式（若本沙盒參與多沙盒組合）

N/A（本沙盒為獨立 DECIDE-gate 能力，未參與 `_integration/` 多沙盒組合）。未來若被某 ADLC agent-build
組合用作收斂閘，再於此記其在組合中貢獻的更高階吸收形式。

## 吸收側 link（adlc CONTEXT 劃界鐵則）

本沙盒由 supply-push 直接 admit 落地（無 open PG 拉動，用戶明示「非幻覺部分直接落地 adlc 沙盒」），
故 absorption 的 bridge_ref = `NONE-direct-admit`（explicit sentinel，永不靜默缺席）；run_records 指向
mega-flow 側待未來 flywheel turn 吸收時補登（吸收管理歸 mega-flow-harness-hub，非本沙盒）。
