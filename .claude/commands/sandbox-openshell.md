---
name: sandbox-openshell
description: "啟動並消費 OpenShell Runtime-containment ADLC 沙盒（launch contract + Dynamic Context Injection 實時狀態快照）。Use when: 啟動沙盒 / containment 驗證 / 在沙盒裡執行 untrusted・agent-generated code。NOT for: 建新沙盒、改沙盒策略、auto-iterate（engine-locus 紅線）。"
argument-hint: "[--sandbox <name>=ns-sandbox] [--probe --iso <ISO>] [--exec \"<cmd>\"]"
allowed-tools: Bash(timeout 12 bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status:*), Bash(timeout 5 sed:*), Bash(timeout 10 docker logs --tail 8 openshell-gateway:*), Bash(bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh up:*), Bash(bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status:*), Bash(python3 sandboxes/openshell-containment/src/sandbox_runner.py:*), Bash(python3 sandboxes/openshell-containment/src/containment_probe.py:*), Bash(echo:*)
activation_injection: true
---

<!-- ════════════════════════════════════════════════════════════════════════
 MIRROR NOTE — 此檔從私有 northstar 的 `.claude/commands/sandbox-openshell.md` 鏡像而來，是 claude code
 **載入/驅動 openshell-containment 沙盒的真實 `/command` 入口**（生產消費關係的消費端）。為公開展示，
 鏡像時做了三處清理：① 描述段原指「能力本體住 execution/scripts/」（northstar 私有佈局）→ 校正為本 repo
 的 `sandboxes/openshell-containment/src/`；② 路由段對私有 mega-flow-harness-hub / adlc plans 的指向 → 標
 withheld；③ **移除**對吸收源 bridge（含 northstar 內部安全架構 mirror，刻意不公開）的路由引用。
 注意命名：本入口名 = `/sandbox-openshell`（manifest 寫的 `/openshell-containment` 是 DOC-ONLY 別名）。
 實際運作過程與真實 live 輸出（gateway Connected / containment_probe 3-case 0-failure）見沙盒的 RUN.md。
 ════════════════════════════════════════════════════════════════════════ -->

# /sandbox-openshell — OpenShell Runtime-containment 沙盒接口（launch + consume，永不 build）

## 描述
per-sandbox 沙盒接口：讓使用者直接觸發已落地的 OpenShell Runtime-containment 能力。本 command =
薄層（同 /self-correcting-loop 形，零新引擎）：**launch contract**（前置 fail-loud → bootstrap up →
Ready 判據 → 消費入口）+ 下方注入的實時沙盒狀態快照。能力本體住
`sandboxes/openshell-containment/src/`（openshell_gateway_bootstrap.sh / sandbox_runner.py /
containment_probe.py），本檔指向不複述。

## 實時沙盒狀態（Dynamic Context Injection — 啟動瞬間快照，非過時猜測）

### ① gateway/container 狀態（bounded：status 輸出按構造 ≤6 行；exit 非 0 = 未 Connected，記錄非 gate）
!`timeout 12 bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status 2>&1 || echo "[gateway-not-connected exit=$?]"`

### ② 最新 containment verdict（record 按構造有界：3 cases × evidence ≤240 chars；sed 截前 40 行）
!`timeout 5 sed -n 1,40p "$(ls -t data/production/containment/*-containment-verdict.json 2>/dev/null | sed -n 1p)" 2>/dev/null || echo "[no-containment-verdict-record]"`

### ③ 沙盒 trace tail（gateway container logs，--tail 8 = 內建截斷，零 pipe）
!`timeout 10 docker logs --tail 8 openshell-gateway 2>&1 || echo "[gateway-container-logs-unavailable exit=$?]"`

## 不變量（違反即停）
- **fail-loud on disabled policy**：若上方任一注入區塊內容是 placeholder 字面文本
  `[shell command execution disabled by policy]` → **立即 ABORT**，輸出指示：「injection 被
  `disableSkillShellExecution` 全域停用；請 (a) 從 settings 移除該 key 後重跑 /sandbox-openshell，
  或 (b) 手動執行下方 launch contract 各命令」。**永不**在無實時狀態下靜默續行（過時猜測 = 本接口
  存在的反命題）。
- **紅線 engine-locus**：本 command 只**啟動 + 注入狀態 + 消費**已落地的沙盒能力。
  **永不** auto-build / auto-iterate / 修改沙盒策略 / 自動重試迴圈。containment_probe 任何
  `failure: true` case = SURFACED gap **交人**（report-only，containment_probe.py 同契約），
  不在本 command 內修。
- **fail-loud 不吞 exit**：launch contract 每步單獨跑、單獨看真實 exit（`; echo EXIT=$?`），
  禁 `| tail` / `| head` 遮蔽。
- **不自動 down**：teardown（`openshell_gateway_bootstrap.sh down`）只在用戶明說時執行。

## 參數
- `$ARGUMENTS`:
  - `--sandbox <name>`：沙盒名（default `ns-sandbox` = sandbox_runner.py DEFAULT_SANDBOX）
  - `--probe --iso <ISO>`：跑 containment 驗證並寫 verdict record（ISO 必由 caller 供，determinism）
  - `--exec "<cmd>"`：在沙盒內執行一條 shell 命令

## 執行步驟（launch contract — 確定性段）
1. **前置條件（fail-loud）**：讀注入區塊 ①。
   - 含 placeholder → 依不變量 ABORT。
   - 顯示 Connected → 跳到步驟 3（沙盒已起，bootstrap 冪等但不必重跑）。
   - 顯示 `[gateway-not-connected …]` 或 container NOT running → 進步驟 2。
2. **啟動**：`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh up --sandbox ns-sandbox; echo EXIT=$?`
   （`--sandbox` 值若用戶以 `--sandbox <name>` 覆寫則代入）。
   - `EXIT=0` = gateway Connected ∧ sandbox Ready（bootstrap 內建 wait_connected + ensure_sandbox，
     兩者任一不達即 die exit 2）。
   - `EXIT=2` = precondition/bootstrap 失敗 → **STOP**，把 stderr 原文交給用戶（常見：docker daemon
     未起、GHCR 拉取失敗）。**禁**自動重試迴圈。
3. **Ready 判據（可選 re-verify）**：`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status; echo EXIT=$?`
   → `EXIT=0` iff gateway Connected。非 0 → STOP 交人。
4. **消費入口**（依 $ARGUMENTS 二選一或依用戶意圖）：
   - **在沙盒執行代碼**：`python3 sandboxes/openshell-containment/src/sandbox_runner.py "<cmd>" -n <sandbox> --timeout 30; echo EXIT=$?`
     → exit = 沙盒內 remote exit code；exit 2 + stderr `transport failure` = gateway/sandbox 不可用
     （回步驟 2）。
   - **containment 驗證**：`python3 sandboxes/openshell-containment/src/containment_probe.py --iso <ISO> -n <sandbox>; echo EXIT=$?`
     → report-only：exit 0 即使有 failure case（讀輸出的 `containment_failures=N`，N>0 = SURFACED
     gap 交人）；exit 1 = precondition 失敗（回步驟 2）。record 落
     `data/production/containment/<ISO>-containment-verdict.json`（containment-verdict/v1）。
5. **收尾**：向用戶回報——gateway/sandbox 狀態、執行了哪個消費入口、真實 exit code、
   （若 --probe）verdict record 路徑 + count_metric。

## 路由
- 沙盒本體 = `sandboxes/openshell-containment/`（src + tests + trace）；接口契約 = 同沙盒 `SKILL.md`；
  wiring 真相 = [`../../sandboxes/PANORAMA.md`](../../sandboxes/PANORAMA.md) `openshell-containment` block（LIVE）。
- 落地脈絡（外部 DR → bridge → build → 對抗驗證）= 同沙盒 `causal-chain.md`；吸收形式 = `absorption-form.md`。
- 沙盒 registry facet、adlc 三-tier 測試規範、吸收源 method-problem-bridge（含 northstar 內部安全架構 mirror）
  = northstar 私有治理層，**刻意未隨附本鏡像**。
