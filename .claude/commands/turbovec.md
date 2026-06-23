---
name: turbovec
description: "在 OpenShell ns-sandbox（default-deny egress）內跑 turbovec 的 air-gapped 本地向量檢索並對抗驗證——index+self-query 全在 containment 內，count_metric==0 = 檢索能跑且沒有東西離開機器。Use when: air-gapped 本地 RAG / 向量檢索 / 驗證 turbovec 在沙盒內可用。NOT for: 建新沙盒、改沙盒策略、auto-iterate（無自動迭代）。"
argument-hint: "[--sandbox <name>=ns-sandbox]"
allowed-tools: Bash(timeout 12 bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status:*), Bash(timeout 6 ls:*), Bash(timeout 12 openshell sandbox exec:*), Bash(openshell sandbox exec:*), Bash(bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh up:*), Bash(bash sandboxes/turbovec/src/stage_turbovec_wheels.sh:*), Bash(python3 sandboxes/turbovec/src/containment_rag_probe.py:*), Bash(echo:*)
activation_injection: true
---

# /turbovec — air-gapped 本地向量檢索（在 containment 內，count_metric==0 = 不出機器）

> 這是 Claude Code 調用 turbovec air-gapped RAG 的 `/command` 入口（生產消費關係的消費端）。
> turbovec **compose openshell-containment**：runtime 住在 `ns-sandbox`（default-deny egress + fs 隔離）內，
> 所以「air-gapped」不是 turbovec 自稱，是 openshell 的邊界**替它**保證的。能力本體住
> `sandboxes/turbovec/src/`（turbovec_rag.py / containment_rag_probe.py / stage_turbovec_wheels.sh），
> 本檔指向不複述。實際運作過程與真實 live 輸出（count_metric=0 / recall_at1=1.0）見沙盒的 `RUN.md`。

## 實時沙盒狀態（Dynamic Context Injection — 啟動瞬間快照，非過時猜測）

### ① compose 前置：openshell gateway/sandbox 狀態（bounded：status 輸出按構造 ≤6 行）
!`timeout 12 bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status 2>&1 || echo "[gateway-not-connected exit=$?]"`

### ② turbovec 是否已 staged 進沙盒（trace tail + ns-sandbox 內 import 探測）
```!
timeout 6 ls -1 sandboxes/turbovec/trace/ 2>/dev/null | tail -3 || echo "[no-trace-yet]"
timeout 12 openshell sandbox exec -n ns-sandbox --no-tty -- sh -c 'python3 -c "import turbovec; print(\"turbovec-staged-in-sandbox\")" 2>&1 | head -1' || echo "[turbovec-not-staged-in-sandbox exit=$?]"
```

> ⚠ C2：上面注入的是**當前 runtime 狀態**（gateway 狀態 + 沙盒內 turbovec 真實版本），非靜態文字。

## 不變量（違反即停）
- **fail-loud on disabled policy**：若上方任一注入區塊是字面 `[shell command execution disabled by policy]`
  → **立即 ABORT**，指示：「injection 被 `disableSkillShellExecution` 全域停用；請從 settings 移除該 key
  後重跑 /turbovec，或手動執行下方 launch contract 各命令」。**永不**在無實時狀態下靜默續行。
- **邊界**：本 command 只**啟動前置 + 注入狀態 + 消費**已落地的 turbovec 能力。
  **永不** auto-build / auto-iterate / 改沙盒策略 / 自動重試。containment_rag_probe 任何 NOT-CONTAINED
  case = SURFACED gap **交人**（report-only），不在本 command 內修。
- **air-gapped 是 AND 條件**：`count_metric==0` 須**檢索能跑（recall 對）∧ egress 被拒**兩者同時為真；
  任一破即非 air-gapped——不可只看 recall 就宣稱 air-gapped。
- **fail-loud 不吞 exit**：launch contract 每步單獨跑、單獨看真實 exit（`; echo EXIT=$?`），
  禁 `| tail` / `| head` 遮蔽（注入區塊 ② 的 `head -1` 是 probe 探測的內建截斷，非 exit 遮蔽）。

## 參數
- `$ARGUMENTS`:
  - `--sandbox <name>`：沙盒名（default `ns-sandbox`）

## 執行步驟（launch contract — 確定性段）
1. **compose 前置（fail-loud）**：讀注入區塊 ①。
   - 含 placeholder → 依不變量 ABORT。
   - 顯示 `Connected` → 進步驟 2。
   - 顯示 `[gateway-not-connected …]` → 先起 openshell：
     `bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh up --sandbox ns-sandbox; echo EXIT=$?`
     （`EXIT=2` = bootstrap 失敗 → **STOP** 交人，禁自動重試）。
2. **staged 確認**：讀注入區塊 ②。
   - 顯示 `turbovec-staged-in-sandbox` → 進步驟 3。
   - 顯示 `[turbovec-not-staged-in-sandbox …]` → 一次性 stage offline wheel：
     `bash sandboxes/turbovec/src/stage_turbovec_wheels.sh; echo EXIT=$?`（host-side、已授權的 abi3 wheel 注入）。
     非 0 → **STOP**，stderr 交人（禁降級偽 verdict）。
3. **消費（air-gapped RAG 對抗驗證）**：
   `python3 sandboxes/turbovec/src/containment_rag_probe.py -n <sandbox>; echo EXIT=$?`
   → report-only：在 `ns-sandbox` 內 build turbovec 索引 + self-query 驗 `recall_at1`，**且**驗 egress 被拒。
   - `count_metric == 0` = air-gapped RAG 成立（recall 對 ∧ egress 拒）→ 印 verdict，終止。
   - `count_metric > 0` = NOT-CONTAINED → 印 + **交人**（SURFACED gap），不在本 command 內修。
   - `EXIT≠0` 且非 count → precondition 失敗（gateway/sandbox 不可用）→ 回步驟 1。
4. **收尾**：向用戶回報——gateway/sandbox 狀態、turbovec 是否 staged、`count_metric`、recall_at1、真實 exit code。

## 路由
- 沙盒本體 = `sandboxes/turbovec/`（src + tests + trace）；接口契約 = 同沙盒 `SKILL.md`；
  wiring 真相 = [`../../sandboxes/PANORAMA.md`](../../sandboxes/PANORAMA.md) `turbovec` block（LIVE）。
- compose 依賴 = [`sandbox-openshell.md`](sandbox-openshell.md)（turbovec 的 runtime 住在它的 `ns-sandbox` 內）。
- 落地脈絡（外部 DR → build → 對抗驗證 → 暴露）見同沙盒 `RUN.md`；吸收源 DR 見 [`../../research/`](../../research/)。
