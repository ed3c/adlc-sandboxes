---
name: arch-fitness
description: >
  Deterministic architecture-fitness Judge/evals standard — measure a target source tree (CODE) against a
  declared arch-model spec (MODEL) and surface the model-code gap: Clean-Arch layer-dependency violations,
  modular-monolith module-boundary breaches, Martin I/A/D coupling (Zone-of-Pain), and AST code smells.
  Cooperates with loop-engineering as the evals standard guiding both macro architecture and micro code.
  觸發詞（triggers）: arch-fitness, 架構適應度, architecture-erosion, model-code-gap, layer-dependency, fitness-function。
allowed-tools: Bash(python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py:*), Bash(timeout 5 python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py:*), Bash(python3 --version)
---

# arch-fitness — 架構適應度 Judge/evals 標準（確定性，消弭模型-代碼縫隙）

> 沙盒接口契約文件：本 SKILL.md 是這個沙盒的接口契約，受沙盒的驗證 gate 機械驗
> （`sandboxes/` 非 skill root，故不被動載入；直接以下方 `arch_fitness_kernel.py` 調用）。
> 分工原則：本沙盒**只量測 + surface + 當 loop 的 Judge/evals 標準**；改不改代碼是人 / loop 的決定（report-only，不自動接受結果）。

## 啟動前置（C5 / fail-loud — 前置不滿足顯式錯誤，禁靜默偽完成）

- 前置檢查: !`python3 --version`

> ☝ 若上面顯示前置**不滿足**（缺 python）→ 顯式報錯 + 記錄 deviation，**禁**降級偽 verdict（fail-loud）。

## 沙盒當前 runtime 狀態（C2 — MUST，≥1 個 live-state 注入）

```!
timeout 5 python3 sandboxes/arch-fitness/src/arch_fitness_kernel.py status 2>&1 || echo "[arch-fitness status unavailable exit=$?]"
```

> ⚠ C2 硬要求：注入的是**當前 runtime 狀態**（最近一次 measure 的 verdict/focus 快照，bounded ≤~6 行）。無量測 →
> 顯式 sentinel `[no measurement yet …]`。**禁**用注入做靜態文字（state snapshot，非 verdict — 閘仍確定性，零 LLM-judge）。

## 能力與調用（沙盒做什麼）

本沙盒被調用時，對一個 target 源碼樹跑確定性 `arch_fitness_kernel.py measure`：

- **宏觀（strategic）**: Clean-Arch 分層依賴規則違規 · 模組化單體 module-boundary 白名單違規 · Martin I/A/D 耦合 + 痛苦區（surfaced 診斷，非二元閘）
- **微觀（tactical）**: Long Method · Too Many Parameters · Large Class（AST 量測的壞味道子集）
- **verdict** = PASS iff 0 hard（layer+boundary）違規；**focus** = 最弱維度 → 導引下一輪 loop 方向
- **Judge/evals 標準**: `rubric` 印出完整概念空間（macro/micro/governance，誠實標 deterministic|semantic|governance）；
  `scorecard` 把確定性維度投影成 `self-correcting-loop` scorecard，供既有 loop 跑 DO→VERIFY→DECIDE（semantic 概念由 loop 的 LLM-VERIFY 評）

## 組合（與 loop-engineering 怎麼接）

- recipe: [`recipes/with-self-correcting-loop.md`](recipes/with-self-correcting-loop.md) — arch-fitness 當 VERIFY + Judge，loop 擁 DO + DECIDE。
- rubric 模板: [`recipes/arch-fitness.rubric.json`](recipes/arch-fitness.rubric.json) — 5 確定性 `runnable` 維度（gated）+ 3 `semantic` `rubric` 維度（LLM 評）。

## 全景圖註冊

本沙盒在 [`../PANORAMA.md`](../PANORAMA.md) 有對應 ```yaml sandbox``` block（沙盒的驗證 gate 機械查）。
