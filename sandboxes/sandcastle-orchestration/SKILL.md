---
name: sandcastle-orchestration
description: >
  RIP/study 載具：真跑 @ai-hero/sandcastle 的「可行組合」(working composition)——sandcastle `head`-run
  (container-isolated agent execution) + 主機端 plain git (branch/commit = merge-back 的 OUTCOME) +
  主機端 exec-gate——於 inner container 對 fixture/throwaway repo，吐確定性 observation-record 給人分流。
  誠實薄 delta：容器隔離跑 ≈ 一般 containment 沙盒，真價值是 sandcastle 的編排設計契約。沙盒只在
  Docker+fixture 邊界內自轉，永不碰宿主自己的工作 repo。觸發詞（triggers）: sandcastle,
  container-isolated agent orchestration, 招牌組合, agent-orchestration RIP study vehicle,
  exec-gate, observation-record, sandcastle-orchestration.
allowed-tools: Bash(docker info:*), Bash(docker ps:*), Bash(timeout 5 docker info:*), Bash(timeout 5 python3 src/boundary_adapter.py:*), Bash(ls:*), Bash(echo:*)
triggers: [sandcastle, container-isolated agent orchestration, 招牌組合, agent-orchestration RIP study vehicle, exec-gate, observation-record, sandcastle-orchestration]
---

# /sandcastle-orchestration — 真跑 sandcastle 可行組合，吐確定性觀察 record

> 接口契約文件：本 SKILL.md 是這個沙盒的接口契約，受沙盒的驗證 gate 機械驗
> （`sandboxes/` 非 skill root，故不被動載入；可調用入口 = `.claude/commands/sandcastle-orchestration.md`）。
> 用 `!`cmd`` dynamic context injection 把沙盒當前 runtime 狀態即時注入 context。
> 邊界原則：RIP run 的 auto-turn（sandcastle `maxIterations`）鎖在 inner container + fixture/throwaway repo
> 邊界內，**碰不到宿主自己的工作 repo**；observation-record 只**遞**給人分流，沙盒不自動接受結果（一個人接受最終結果）。

## 啟動前置（C5 / 啟動方式；fail-loud — 前置不滿足顯式錯誤，禁靜默偽完成）

RIP run（`src/run_sandcastle.ts`）需 Docker daemon up + Node + 一次性 OAuth token（容器內 agent）。invocation-time 注入真狀態：

- Docker daemon 前置檢查（daemon up → 印 ServerVersion）: !`timeout 5 docker info --format '{{.ServerVersion}}' 2>&1 | head -1 || echo "[docker-down exit=$?]"`

> ☝ 若上方顯示 `[docker-down …]` 或無 ServerVersion → 顯式報錯 + 記 deviation，**禁**降級偽 RIP run（fail-loud）。

## 沙盒當前 runtime 狀態（C2 — MUST，≥1 個 live-state 注入）

注入沙盒當前狀態快照（Docker daemon 是否 up + 對最近一筆 result 的確定性投影首行，若有）——RIP 接口級實現，
讓下一輪 RIP run / 分流基於真實狀態而非過時猜測：

```!
timeout 5 docker info >/dev/null 2>&1 && echo "docker daemon: UP (sandbox can run)" || echo "docker daemon: DOWN"
timeout 5 python3 src/boundary_adapter.py emit --result tests/fixtures/result.sample.json --iso 2026-06-24 2>&1 | head -1 || echo "[no fixture]"
```

> ⚠ C2 硬要求：上面注入的是**當前 runtime 狀態**（真 stdout：docker daemon 活否 + adapter 對最近 result 的首行投影），
> **非**靜態文字。docker 未起 → `docker daemon: DOWN`（正常，沙盒不能跑時的誠實態）。

## 能力與調用（沙盒做什麼 — 可行組合，誠實薄 delta）

`/sandcastle-orchestration` 被調用時，**人 on-demand** 跑一次 RIP run（Path A，`src/run_sandcastle.ts`）跑**可行組合**：
sandcastle `head`-run（container-isolated agent execution，✅ work on macOS docker）+ **主機端 plain git**
（`checkout -B branch` → `commit` = branch merge-back 的 OUTCOME）+ **主機端 exec-gate**（stage 間確定性 `node --test`）
於 inner container 對 fixture/throwaway repo，dump `result.json`；再經 boundary adapter（Path B，`src/boundary_adapter.py`）
確定性投影成 observation-record，遞給人分流。

> **誠實薄 delta**：sandcastle **自己**的 git-worktree branch-merge-back 在 macOS docker 下**壞**
> （`patchGitMountsForWindows` 的 gitdir 修正 `if (platform !== "win32") return` 是 Windows-only），故本組合**刻意繞開**它、
> 用主機端 plain git 代替——**merge-back 不是 sandcastle 的能力宣稱**。可行的那半（容器隔離跑）≈ 一般 containment 沙盒；
> 真 delta = sandcastle 的**編排設計契約**（provider-agnostic + implement→exec-gate→review + iteration/prompt ergonomics）。

## 誠實邊界（硬約束）

本沙盒**只**暴露「真跑 sandcastle 可行組合 + 確定性觀察」這一能力半，**明確未封裝**：
- sandcastle 其餘特性（Vercel provider / interactive TUI / podman / 自有 worktree merge-back）= 後續若無 demand 即不納；
  自有 worktree merge-back 在 macOS docker **本就壞**（非選擇不納而是 broken，誠實記於本沙盒 `RUN.md`）。
- **自動接受結果 / 自動 land** = 紅線：observation-record 只**遞**給人分流節點，哪個 delta 真 land 是後續人類決策（非自動）。
- RIP run 的「對」靠真跑一次（RIP）證明，**不用 MagicMock 假測**（agent 非確定）；確定性那半（boundary adapter）由嚴測覆蓋（42 tests + selftest exit 0）。

## 兩條路徑與真實運作

- Path A（probabilistic RIP run）= `src/run_sandcastle.ts`，需 Docker + Node + OAuth token。
- Path B（deterministic projection）= `src/boundary_adapter.py`，純 python3、無外部依賴，本 repo 即真實可跑（`selftest`）。
- 實際運作過程與真實 live 輸出見同沙盒的 [`RUN.md`](RUN.md)。

## 全景圖註冊（存在 ≠ 接線）

本沙盒須在 [`../PANORAMA.md`](../PANORAMA.md) 有對應 ```yaml sandbox``` block（沙盒的驗證 gate 機械查）。
