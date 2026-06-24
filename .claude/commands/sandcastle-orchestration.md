---
name: sandcastle-orchestration
description: "RIP/study 載具：真跑 @ai-hero/sandcastle 可行組合 (working composition: sandcastle head-run container-isolated agent execution + 主機端 plain git branch/commit = merge-back OUTCOME + 主機端 exec-gate) 於 inner container 對 fixture/throwaway repo，吐確定性 observation-record 給人分流。誠實薄 delta：容器隔離跑 ≈ 一般 containment 沙盒，真價值是 sandcastle 編排設計契約。Use when: 啟動 sandcastle 沙盒、真跑 container-isolated agent orchestration 可行組合、做 agent-orchestration RIP study。NOT for: 建新沙盒、改沙盒策略、自動接受結果（沙盒永不碰宿主自己的工作 repo，land 由人裁）。"
argument-hint: "[--fixture <name>] [--max-iterations <N>] [--iso <ISO>]"
allowed-tools: Bash(timeout 5 docker info:*), Bash(docker info:*), Bash(docker ps:*), Bash(ls:*), Bash(grep:*), Bash(echo:*)
activation_injection: true
---

# /sandcastle-orchestration — 真跑 sandcastle 可行組合，吐確定性觀察 record（人 on-demand）

> 這是 Claude Code **載入 / 驅動本沙盒的真實 `/command` 入口**（生產消費關係的消費端）。能力本體在
> `sandboxes/sandcastle-orchestration/src/`（Path A `run_sandcastle.ts` + Path B `boundary_adapter.py`）。
> 實際運作過程與真實輸出見同沙盒的 `RUN.md`。

## 描述
薄層 command（同其它沙盒入口形，零新引擎）：人 on-demand 驅動一次 RIP run（Path A，sandcastle
**可行組合**於 inner container 對 fixture/throwaway repo），dump `result.json`；經 boundary adapter（Path B，
`sandboxes/sandcastle-orchestration/src/boundary_adapter.py`，本檔指向不複述）確定性投影成 observation-record，
遞給人分流。可行組合 = sandcastle `head`-run（容器隔離跑）+ **主機端 plain git**（branch/commit = merge-back OUTCOME）
+ **主機端 exec-gate**；**刻意繞開** sandcastle 自有 worktree merge-back（macOS docker 下 run() **真跑壞**：worktree-id/session-capture，**非** win32 gitdir patch；見 RUN.md §4 真跑驗證）。
邊界：auto-turn 鎖 inner container + fixture/throwaway repo，**沙盒永不碰宿主自己的工作 repo**；land 由人裁。

## 實時沙盒狀態（Dynamic Context Injection — 啟動瞬間快照，非過時猜測）

### Docker daemon + 最近 observation-record（bounded：按構造 ≤~4 行；無 record 時顯式 sentinel）
!`timeout 5 docker info >/dev/null 2>&1 && echo "docker daemon: UP (sandbox can run)" || echo "docker daemon: DOWN"`
!`ls -1 sandboxes/sandcastle-orchestration/trace/ 2>/dev/null | grep -E 'observation-record|rip-result' | tail -2 || echo "[no-observation-record-yet]"`

## 不變量（違反即停）
- **fail-loud on disabled policy**：若上方注入是字面 `[shell command execution disabled by policy]`
  → **立即 ABORT**，指示：「injection 被 `disableSkillShellExecution` 全域停用；請從 settings 移除該 key
  後重跑，或手動執行 `docker info` + `ls sandboxes/sandcastle-orchestration/trace/`」。
  **永不**在無實時狀態下靜默續行（過時猜測 = 本接口存在的反命題）。
- **fail-loud on docker down**：若注入顯示 `docker daemon: DOWN` → **停下報錯**，指示先起 Docker daemon，
  **禁**降級偽 RIP run（fail-loud）。
- **邊界**：本 command 只**驅動一次 RIP run + 注入狀態 + 產 observation-record**。
  RIP run 的 auto-turn 鎖 inner container + fixture/throwaway repo，**沙盒永不對宿主自己的工作 repo 動手**。
  observation-record 只**遞**給人分流，**永不**自動 land / 自動接受結果。
- **誠實薄 delta**：本 command 不宣稱 sandcastle 自有 worktree merge-back 為能力（它壞）；
  merge-back OUTCOME 走主機端 plain git。真 delta（編排設計契約）由人後續評估，不在此斷言。
- **RIP-settles-behavior**：sandcastle（或任何 repo）的 runtime/behavioral claim（如 merge-back 在某平台可不可用）
  **只能靠一次完整 RIP 真跑定案**——源碼讀 / 窄 probe 都會 over-reach。實證見 RUN.md §4（窄 probe 一度誤推
  「merge-back works」，完整 `run()` RIP 才證 macOS 真壞）。
- **fail-loud 不吞 exit**：注入分支顯式 `|| echo "…"`；禁 `| tail` / `| head` 吞 exit。

## 參數
- `$ARGUMENTS`:
  - `--fixture <name>`：RIP run 的 throwaway 目標 repo 種子（runner copy `fixture/` 進 throwaway + git init）
  - `--max-iterations <N>`：sandcastle `maxIterations` 上界（有界迴圈）
  - `--iso <ISO>`：本次時戳（determinism；caller 供）

## 執行步驟（一次 = 一次調用；人 on-demand）
1. **讀注入**：上方 Docker daemon + 最近 observation-record。含 disabled-policy placeholder → 依不變量 ABORT；`docker daemon: DOWN` → 依不變量停下報錯。
2. **RIP run（Path A）**：跑可行組合 `head` agent → 主機端 exec-gate → review agent → 主機端 plain git `checkout -B branch` → `commit`（merge-back OUTCOME）於 inner container 對 fixture/throwaway repo → dump `result.json`。
   （Path A 需 Docker + Node + 一次性 OAuth token；token 放 throwaway repo 的 `.sandcastle/.env`，目標 repo 預設在 `$TMPDIR/sandcastle-target`，可 `SANDCASTLE_TARGET` 覆寫。）
3. **boundary adapter（Path B）**：`python3 src/boundary_adapter.py emit --result <rip-result.json> --iso <ISO>` → observation-record（確定性投影，純 python3、無 Docker/token）。
4. **分流**：observation-record → 遞給人分流候選（哪個 delta 真 land = 人裁）。
5. **收尾**：回報 RIP run 的 iteration 數 / host-git merge-back sha / exec-gate verdict + observation-record 路徑；**不**自動 land。

## 路由
- RIP run + adapter owner（全景圖）= `sandboxes/sandcastle-orchestration/`（[`../../sandboxes/PANORAMA.md`](../../sandboxes/PANORAMA.md) `sandcastle-orchestration` block）。
- 落地脈絡（外部編排設計 → 可行組合 → 真跑驗證 → 暴露）見同沙盒 `RUN.md`。
- 對位（force-verify-already-have 候選）：openshell-containment（容器隔離）/ 主機端 plain git（merge-back OUTCOME）/ self-correcting-loop（rubric DECIDE）。
