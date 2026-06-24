<div align="center">

# adlc-sandboxes

**Four small, self-contained sandboxes — each turns one external idea into a runnable, deterministically-verified capability you can invoke as a Claude Code `/command`.**

![sandboxes](https://img.shields.io/badge/sandboxes-4-blue)
![tests](https://img.shields.io/badge/tests-80_passing-brightgreen)
![runtime](https://img.shields.io/badge/runtime-python3-blue)
![API keys](https://img.shields.io/badge/API_keys-zero-success)
![status](https://img.shields.io/badge/status-showcase-lightgrey)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<br>

*Each `SKILL.md` is a real Claude Code `/command` definition. Each sandbox ships green tests.*
*"Done / contained / air-gapped" is a machine fact — an exit code, a count, a real score — never an LLM's claim.*

> **Design intent.** Each sandbox isolates ONE capability behind a deterministic gate, exposed as a
> `/command` whose entry injects the sandbox's live runtime state at call time. Every sandbox ships a
> one-command green test entry (`bash run-tests.sh`); two need extra infra for their full live
> capability. See [Honest boundary](#honest-boundary).

[What](#what-this-is) · [Sandboxes](#sandboxes) · [Quick verify](#quick-verify) · [Usage](#usage) · [Sources](#absorbed-sources-dr)

</div>

---

```
   EXTERNAL IDEA            LANDED SANDBOX              INTERFACE  ·  PROOF
 ┌───────────────┐        ┌──────────────────┐        ┌────────────────────┐
 │  DR / prompt  │ absorb │   src/ + tests   │ expose │ SKILL.md = /command│
 │  (research/)  │───────▶│  (green, mocked  │───────▶│  + PANORAMA wiring │
 │               │        │   boundary)      │        │  + !`cmd` injection│
 └───────────────┘        └──────────────────┘        └────────────────────┘

 zero-trust DR  ───▶  openshell-containment  ───▶  /sandbox-openshell        [LIVE]
 embedded-vec DR ──▶  turbovec               ───▶  /turbovec                 [LIVE]
 user protocol  ───▶  self-correcting-loop   ───▶  /self-correcting-loop     [LIVE]
 sandcastle orch ─▶  sandcastle-orchestration ──▶  /sandcastle-orchestration [LIVE*]

 *Path B (deterministic observation-record projection) is LIVE on python3 alone;
  Path A (the probabilistic RIP run) additionally needs Docker + Node + a Claude OAuth token.
```

---

## What this is

**設計意圖**：每個沙盒 = 把**一個外部想法**落地成一個**自洽的小 project**，遵循同一套設計原則：

- **一個能力、一個沙盒**：各沙盒只隔離一件事——enforced containment 執行 / air-gapped 本地向量檢索 /
  自我修正迴圈的確定性 DECIDE 閘。
- **確定性閘優於 LLM-judge**：「達標 / contained / air-gapped」由確定性 kernel 裁——exit code、
  `count_metric`、真實分數——**不是 agent 的散文宣稱**。
- **`/command` 接口 + 即時狀態注入**：能力以 Claude Code `/command` 暴露，入口在調用瞬間用 `!`cmd``
  dynamic context injection 把沙盒**當前 runtime 狀態**注入 context，讓模型基於真實狀態而非過時猜測行動。
- **compose 既有層、不造新引擎**：每個沙盒只新增最小的那一塊（如 `self-correcting-loop` 只新增 DECIDE 閘，
  PLAN/DO/VERIFY 復用既有 loop 層）。
- **人決定 WHAT、人接受結果**：target / rubric / 何時調用 / 是否接受由人定；沙盒只跑確定性那一步——
  **沒有自動接受結果、自動續跑的循環**。

每個沙盒的真實運作（生產消費循環 + live transcript）見各 [`RUN.md`](sandboxes/)；通用框架見
[`PRODUCTION-CONSUMPTION.md`](PRODUCTION-CONSUMPTION.md)。

---

## Sandboxes

**沙盒一覽（4 個全完成單元）**

| 沙盒 | 暴露能力 | `/command` | 一鍵跑綠 | live 能力另需 |
|------|---------|-----------|----------|-------------|
| `openshell-containment` | OpenShell default-deny egress + fs 隔離下的 enforced-containment 執行 + 對抗式 containment_probe（count_metric==0 = 完全 contained） | `/openshell-containment` · `/sandbox-openshell` | ✅ 8 passed | OpenShell + Docker |
| `turbovec` | air-gapped 本地向量檢索——index+self-query 全在 containment 內（count_metric==0 = 不出機器；composes openshell-containment） | `/turbovec` | ✅ 5 passed | 上者 + staged wheels |
| `self-correcting-loop` | PLAN/DO/VERIFY/DECIDE 的確定性 DECIDE 閘——∀criterion ≥ threshold → FINAL，否則 ITERATING + 最弱項；有界 no-progress / exhaustion 守衛；零 LLM-judge | `/self-correcting-loop` | ✅ 25 passed + selftest 6/6 | 無（live 也只需 python3） |
| `sandcastle-orchestration` | 真跑 @ai-hero/sandcastle 可行組合（head-run 容器隔離 agent + 主機端 plain git = merge-back OUTCOME + 主機端 exec-gate）對 fixture/throwaway repo，確定性投影成 observation-record | `/sandcastle-orchestration` | ✅ 42 passed + selftest 7/7 | Path A RIP run 另需 Docker + Node + Claude OAuth token（Path B 投影只需 python3） |

全景圖（機械可驗的 wiring 真相）：[`sandboxes/PANORAMA.md`](sandboxes/PANORAMA.md)。

---

## Quick verify

**一鍵證明每個沙盒可跑。** clone 後**從 repo 根**跑：

```bash
bash run-tests.sh
# → 4 沙盒的 test 套件 + 2 個 selftest，全綠時 exit 0：
#   self-correcting-loop · selftest ✅ / pytest 25 ✅ · openshell-containment 8 ✅ · turbovec 5 ✅
#   · sandcastle-orchestration · selftest ✅ / pytest 42 ✅ → ALL GREEN（80 passing）
```

只需 `python3` + `pytest`（`pip install pytest`）——**無** Docker / OpenShell / Ollama（測試把外部邊界 mock 掉）。
每個沙盒因此都有可立即跑綠的入口；下方 [Usage](#usage) 再分（A）當 Claude Code skill 調用、（B）跑底層真實能力。

---

## Usage

**這些 `SKILL.md` 就是 `/command`。** 每個 `sandboxes/<name>/SKILL.md` 是一份**完整的 Claude Code skill 定義**
——frontmatter `name`（= `/command` 名）+ `description`（含觸發詞）+ `allowed-tools`（限定 Bash 權限）+ body 用
`!`cmd`` **dynamic context injection** 在調用時把沙盒當前 runtime 狀態的真 stdout 注入 context。兩條路徑：

> 📂 **想直接看「每個沙盒實際跑起來長什麼樣 / 它在 Claude Code 的生產消費關係」** → 讀
> [`PRODUCTION-CONSUMPTION.md`](PRODUCTION-CONSUMPTION.md)（總覽）＋ 各 `sandboxes/<name>/RUN.md`（真實 live transcript）。

### A — 當成 Claude Code skill / `/command` 用

本 repo **隨附三個 `/command` 入口**（[`.claude/commands/`](.claude/commands/)：`self-correcting-loop.md` ·
`sandbox-openshell.md` · `turbovec.md`）。clone 後把本 repo 當 project 開（**cwd 在 repo 根**），
`/self-correcting-loop`、`/sandbox-openshell`、`/turbovec` 即可直接調用（`/turbovec` compose openshell-containment，
入口的 launch contract 會先確認 openshell gateway + turbovec staged 兩個前置）。

也可把單一沙盒接成你自己的 skill：

```bash
mkdir -p ~/.claude/skills/self-correcting-loop
ln -s "$PWD/sandboxes/self-correcting-loop/SKILL.md" ~/.claude/skills/self-correcting-loop/SKILL.md
```

> **cwd / 路徑很重要**：SKILL.md 與入口的 `!`cmd`` 注入用 **repo-relative 路徑**（`sandboxes/<name>/src/...`）。
> 調用時 cwd 要在 repo 根；若把 SKILL.md copy 到別處，請同步改 `src/` 路徑。

### B — 直接跑底層能力（不需 Claude Code）

每個沙盒真實邏輯在 `src/`；manifest 的 `runtime_trace_cmd` 是正規自驗調用。**從 repo 根**跑：

```bash
# self-correcting-loop — 純 python3，立即可跑（已驗 selftest 6/6 PASS）
(cd sandboxes/self-correcting-loop && python3 src/loop_kernel.py selftest --iso 2026-06-23)

# 一輪實際用法：LLM 產出 artifact + 對 rubric 評分寫成 scorecard JSON，kernel 確定性裁決：
(cd sandboxes/self-correcting-loop && \
  python3 src/loop_kernel.py decide \
    --rubric src/fixtures/rubric.json --scorecard src/fixtures/scorecard-final.json \
    --loop demo --iso 2026-06-23)
# → FINAL(exit 0) iff 每條 criterion ≥ threshold；否則 ITERATING(exit 3) + 最弱失敗項

# openshell-containment — 需先裝 OpenShell CLI + Docker
bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status   # 非 Connected →
bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh up --sandbox ns-sandbox
python3 sandboxes/openshell-containment/src/containment_probe.py --iso 2026-06-23

# turbovec — 需 openshell-containment 就緒 + 一次性 stage 離線 wheel
bash sandboxes/turbovec/src/stage_turbovec_wheels.sh
python3 sandboxes/turbovec/src/containment_rag_probe.py -n ns-sandbox

# sandcastle-orchestration — Path B（確定性投影）純 python3，立即可跑（selftest 7/7）
(cd sandboxes/sandcastle-orchestration && python3 src/boundary_adapter.py selftest --iso 2026-06-24)
(cd sandboxes/sandcastle-orchestration && \
  python3 src/boundary_adapter.py emit --result tests/fixtures/result.sample.json --iso 2026-06-24)
# → 把一份 rip-result.json 純函數投影成 observation-record（container-isolation / exec-gate verdict /
#   branch-merge-back-outcome / token / 多階段）

# sandcastle-orchestration — Path A（真 RIP run）另需 Docker + Node + 一次性 Claude OAuth token
#   token 放 throwaway repo 的 .sandcastle/.env；目標 repo 預設 $TMPDIR/sandcastle-target（SANDCASTLE_TARGET 可覆寫）
(cd sandboxes/sandcastle-orchestration && npx tsx src/run_sandcastle.ts)
```

---

## Honest boundary

**誠實邊界（什麼能跑、什麼需要設定）：**

- **每個沙盒都可一鍵跑綠**（`bash run-tests.sh`，只需 python3 + pytest，**無** Docker / OpenShell / Ollama / Node / token）：
  openshell-containment 8 · turbovec 5 · self-correcting-loop 25 + selftest 6/6 · sandcastle-orchestration 42 + selftest 7/7
  （共 80 passing）。測試把外部邊界 mock / 投影掉。
- **完整 live 能力**：`self-correcting-loop` 純 python3 即為 live；`openshell-containment`（真實 enforced containment）
  需 OpenShell CLI + Docker；`turbovec`（air-gapped RAG）再加一次性 staged wheels；`sandcastle-orchestration`
  的 **Path B**（observation-record 投影）純 python3 即 live，**Path A**（probabilistic RIP run = 容器內 agent 真跑）
  另需 Docker + Node + 一次性 Claude OAuth token（agent run 非確定，故靠真跑一次證明，不 mock）。重型 probe 會寫
  `trace/...`，首次跑可能要先 `mkdir -p` 該輸出目錄。
- **入口**：隨附 `.claude/commands/` 四個入口（`self-correcting-loop.md` · `sandbox-openshell.md` · `turbovec.md`
  · `sandcastle-orchestration.md`）是 Claude Code 載入 / 驅動沙盒的真入口（`/turbovec` compose openshell-containment）。
  各沙盒實際運作見 `RUN.md`，框架見 `PRODUCTION-CONSUMPTION.md`。
- **Zero-API-Key**：常駐檢索 / 嵌入 / rerank 100% 本地化（Ollama），**無雲端 key**。

---

## Absorbed sources (DR)

每個沙盒是把一個外部想法**落地**的結果；那些想法的源頭 Deep Research 報告放在 [`research/`](research/)：

- `openshell-containment` ← 「NVIDIA Open Shell + LangChain Deep Agents 零信任架構」DR
- `turbovec` ← 「embedded 向量資料庫 / turbovec / TurboQuant RAG 重構」DR
- `self-correcting-loop` ← 無 DR（源自使用者 prompt 協定）
- `sandcastle-orchestration` ← 無 DR（直接吸收 `@ai-hero/sandcastle` 的容器隔離 agent 編排設計契約；
  誠實邊界：live RIP run 需 Docker + Node + Claude OAuth token，自有 worktree merge-back 在 macOS docker 下本就壞，故繞開）

> ⚠ DR 是**原始綜述、非 vetted fact**——吸收時的 external-verify 抓出多處 overstated / 未查證宣稱
> （詳 [`research/README.md`](research/README.md)）。把這兩份 DR 當**原始吸收輸入**讀，不是已查證事實。

---

## Layout

```
adlc-sandboxes/
├── run-tests.sh              ← 一鍵 runnable proof（3 沙盒 test + selftest 全綠）
├── PRODUCTION-CONSUMPTION.md ← 沙盒在 Claude Code 的生產消費關係（總覽）
├── .claude/commands/         ← /command 入口（self-correcting-loop · sandbox-openshell · turbovec · sandcastle-orchestration）
├── research/                 ← 各沙盒吸收的源 DR 報告（raw Gemini DR export，非 vetted fact）
└── sandboxes/
    ├── PANORAMA.md           ← 全景圖（沙盒 wiring 的 live 真相；機器可解 yaml block）
    └── <name>/
        ├── SKILL.md          ← 沙盒接口契約 = Claude Code skill 定義（frontmatter name = /command 名）
        ├── RUN.md            ← 實際運作過程與結果（生產消費循環 + 真實 live transcript）
        ├── manifest.yaml     ← 機器可解的能力清單 + 啟動宣告
        └── src/  tests/  trace/
```

每個 `SKILL.md` 提供：

- **frontmatter**：`name`（= `/command` 名）/ `description`（含觸發詞）/ `allowed-tools`。
- **≥1 個 `!`cmd`` 即時狀態注入**：body 至少一處用 dynamic context injection 把沙盒**當前 runtime 狀態**注入 context。
- **`PANORAMA.md` 登記**：一筆 row + 一個機器層 yaml block（存在 ≠ 接線）。

---

## License

MIT — see [`LICENSE`](LICENSE). 涵蓋本 repo 的沙盒代碼與文檔；`research/` 的 DR 是外部研究綜述（raw，非 vetted fact），保留原作脈絡。

---

<div align="center">

*內容語言以中文為主、hero 雙語。*

</div>
