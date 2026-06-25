---
name: capacity-estimation
description: >
  Deterministic AI-Agent capacity estimator + feasibility rubric judge, encoding the complete
  framework of the DR "AI Agent 時代的計算系統容量估算與架構設計研究報告". Given an agent-system spec
  it computes the DR's five core metrics (Agent QPS amplification, Input/Output token throughput TPS,
  GPU VRAM = model weights + KV cache, prefix-cache breakeven, RAG vector-DB RAM) and JUDGES feasibility
  against budgets — FEASIBLE iff every budgeted criterion is within budget, else INFEASIBLE + the binding
  constraint + the DR's macro architecture lever (how many GPU cards / tensor-parallel size / vector-DB RAM)
  AND micro code lever (PagedAttention / FP8 KV quant / RadixAttention / SQ8 / DiskANN). "FEASIBLE" is
  entailed by actual numbers vs budgets, never an agent's prose (zero LLM-judge). 觸發詞:
  capacity-estimation, 容量估算, agent-capacity, vram-sizing, kv-cache, token-throughput, gpu-sizing,
  capacity-feasibility, 代理放大係數, 架構檢核表.
allowed-tools: Bash(timeout 5 python3 sandboxes/capacity-estimation/src/capacity_kernel.py:*), Bash(python3 sandboxes/capacity-estimation/src/capacity_kernel.py:*), Bash(python3 --version), Bash(echo:*)
triggers: [capacity-estimation, 容量估算, agent-capacity, vram-sizing, kv-cache, token-throughput, gpu-sizing, capacity-feasibility, 代理放大係數, 架構檢核表]
---

# capacity-estimation — AI-Agent 容量估算器 + 可行性 rubric judge（DR 完整框架的確定性編碼）

> 沙盒接口契約文件：本 SKILL.md 是這個沙盒的接口契約，受沙盒的驗證 gate 機械驗
> （`sandboxes/` 非 skill root，故不被動載入；可調用入口 = [`.claude/commands/capacity-estimation.md`](../../.claude/commands/capacity-estimation.md)，或直接跑下方 `capacity_kernel.py`）。
> 分工原則：kernel 只做確定性**估算 + 可行性裁定**（formulas + budget 比較）；spec/budgets 由人提供、
> FEASIBLE/INFEASIBLE 結果與架構決策由人接受——本接口不自動接受結果（一個人接受最終結果）。

## 啟動前置（C5 / fail-loud — 前置不滿足顯式錯誤，禁靜默偽完成）

kernel 是純 python，無外部依賴（無 Ollama / 無網路 / 無 datetime.now）。invocation-time 注入真狀態：

- 前置檢查（python present → exit 0）: !`python3 --version`

> ☝ 若缺 python（上方無版本輸出）→ 顯式報錯，**禁**偽造估算/裁定結果（fail-loud）。

## 沙盒當前 runtime 狀態（C2 — MUST，≥1 個 live-state 注入）

注入當前 capacity-loop 狀態快照（迭代數 / 上輪 FEASIBLE·INFEASIBLE / 綁定約束）的真 stdout——讓下一輪
架構調整基於真實 verdict 而非過時猜測聚焦綁定約束：

```!
timeout 5 python3 sandboxes/capacity-estimation/src/capacity_kernel.py state --loop default 2>&1 || echo "[no-loop-state exit=$?]"
```

> ⚠ C2 硬要求：上面注入的是**當前 capacity-loop runtime 狀態**（真 stdout），非靜態文字。
> 首次調用尚無 state → 顯示 `[no-loop-state: default]`（正常，第一輪 judge --loop 後即有）。

## 能力與調用（沙盒做什麼）

本沙盒把 DR 的「§5 架構檢核表」機械化成一個確定性估算器 + 可行性 judge（src seam = `src/capacity_kernel.py`）：

1. **estimate**（確定性）：`capacity_kernel.py estimate --spec SPEC.json` → 算 DR 五步指標
   （Agent QPS / Input·Output TPS / 權重+KV 顯存 / 前綴快取 breakeven / RAG RAM），bytes 精確 + GiB·GB 雙單位。
2. **judge**（確定性 rubric）：`capacity_kernel.py judge --spec SPEC.json --budgets BUDGETS.json --loop NAME --iso ISO`
   → `FEASIBLE`(exit 0) iff 每條**有 budget** 的 criterion 都在預算內；否則 `INFEASIBLE`(exit 3) + 綁定約束清單，
   每條綁定帶 DR 的**宏觀架構槓桿**（買幾張卡 / TP 規模 / Vector DB RAM）與**微觀代碼槓桿**
   （PagedAttention / FP8 KV / RadixAttention / SQ8 / DiskANN）；同時 advance loop-state。
   無 budget 的 criterion 標 `not_constrained`（資訊性，永不 fail）——partial budget 不偽造 verdict。
3. **state**（DCI 注入源）：`capacity_kernel.py state --loop NAME` → 有界 loop-state 快照。
4. **scorecard**（fleet loop 投影）：`capacity_kernel.py scorecard --spec SPEC.json --budgets BUDGETS.json [--dims ...]`
   → 把 budgeted criteria 投影成 `/self-correcting-loop` 的 loop_kernel-相容 runnable scorecard（`{id: exit_code}`，
   0=within budget / 1=BINDING；keys==rubric ids），讓 loop **多 criterion** DECIDE（focus 指向綁定的 DR step）。
   DECIDE 交 loop_kernel，本 kernel 只 measure+project（no new engine，mirror arch-fitness scorecard_from_report）。

### 配合迴圈工程作 Judge / evals 標準（核心組合，真組合非新引擎）

`judge` 的 exit 0/3 與 `self-correcting-loop` 的 DECIDE FINAL/ITERATING **同語意**——故本 judge 可直接當
`/self-correcting-loop` rubric 裡的一條 `kind: runnable` criterion（VERIFY 跑
`capacity_kernel.py judge ...; echo EXIT=$?`，exit 0 = 該軸 pass）。當 LLM 迭代一個 agent 系統架構時，
DECIDE 就多一條**確定性「capacity-feasible」軸**，INFEASIBLE 時 judge 把下一輪指向綁定約束 + DR 槓桿，
**同時引導宏觀 sizing 與微觀代碼方向**。組合配方見
[`recipes/with-self-correcting-loop.md`](recipes/with-self-correcting-loop.md) +
[`recipes/capacity-estimation.rubric.json`](recipes/capacity-estimation.rubric.json)。

bundled fixtures（`src/fixtures/dr-example-spec.json`）= DR §2/§5 實戰範例（自動化數據分析 Agent,
Llama-3-70B）供 `selftest` 自驗（忠實複現 40 QPS / 327680 B KV/token / 140GB 權重 / 184.32GB RAG +
judge 判別性）。底層 seam 是純函數 kernel。

## 誠實邊界（硬約束）

本沙盒**只**機械化 DR 的**容量估算 + 可行性裁定**，**明確未封裝**：
- **實際 LLM 推理 / benchmark 實測**：kernel 是 back-of-envelope 估算（DR 自身定位），非真跑 vLLM/SGLang 量測。
- **架構決策本身**：kernel 算數字 + 標綁定約束 + 給 DR 槓桿；**買不買卡、開不開 FP8 由人接受**（report-only）。
- **DR 數值精度**：DR 的範例數字是 illustrative；kernel 忠實複現之，並以 spec 接收使用者真實參數。DR 自身混用
  GB(十進位)/GiB(二進位)，kernel 一致化成 bytes + 雙單位（見 `docs/dr-formula-inventory.md`）。
- **優化技術的真實實現**：PagedAttention/RadixAttention/SQ8/DiskANN 是 DR 援引的既有系統能力，kernel 只**援引其
  量化效果作為槓桿建議**，不重實作這些引擎。唯一新增 = 確定性估算+judge 閘（composed not rebuilt，no new engine）。

## DR 公式溯源

DR 公式溯源（49 圖轉錄 + 5 步檢核表）: [`docs/dr-formula-inventory.md`](docs/dr-formula-inventory.md)

## 全景圖註冊

本沙盒在 [`../PANORAMA.md`](../PANORAMA.md) 有對應 ```yaml sandbox``` block（沙盒的驗證 gate 機械查三方名一致）。
