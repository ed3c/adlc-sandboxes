<div align="center">

# adlc-sandboxes

**Three RIP-proven ADLC sandboxes — each an external idea *landed* as a self-contained, runnable mini-project — mirrored from a private demand-pull capability system (codename _northstar_).**

![sandboxes](https://img.shields.io/badge/sandboxes-3-blue)
![tests](https://img.shields.io/badge/tests-38_passing-brightgreen)
![runtime](https://img.shields.io/badge/runtime-python3-blue)
![API keys](https://img.shields.io/badge/API_keys-zero-success)
![status](https://img.shields.io/badge/status-raw__mirror_showcase-lightgrey)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<br>

*Not a product to install — a showcase to read, run, and learn from.*
*Each `SKILL.md` is a real Claude Code `/command` definition. Each sandbox ships green tests.*

> **Showcase, not a product.** The orchestration / gate / governance layer that *runs* these in
> `northstar` is private and **not** in this repo — so the **live** capability of two sandboxes needs
> extra infra. But every sandbox has a one-command green test entry (`bash run-tests.sh`). See
> [Honest boundary](#honest-boundary).

[What](#what-this-is) · [Sandboxes](#sandboxes) · [Quick verify](#quick-verify) · [Usage](#usage) · [Sources](#absorbed-sources-dr) · [Invariants](#design-invariants)

</div>

---

```
   EXTERNAL IDEA            LANDED SANDBOX              INTERFACE  ·  PROOF
 ┌───────────────┐        ┌──────────────────┐        ┌────────────────────┐
 │  DR / prompt  │ absorb │   src/ + tests   │ expose │ SKILL.md = /command│
 │  (research/)  │───────▶│  (green, mocked  │───────▶│  + PANORAMA wiring │
 │               │        │   boundary)      │        │  + !`cmd` injection│
 └───────────────┘        └──────────────────┘        └────────────────────┘

 zero-trust DR  ───▶  openshell-containment  ───▶  /sandbox-openshell      [LIVE]
 embedded-vec DR ──▶  turbovec               ───▶  /turbovec               [LIVE]
 user protocol  ───▶  self-correcting-loop   ───▶  /self-correcting-loop   [LIVE]
```

---

## What this is

**北極星本質**：northstar = 一套私有的 *demand-pull 能力獲取系統*——把一個外部想法變成 LLM 在 repo 內 runtime
行為的真實改變，且不把「讀過了 / 長得像」當「長了能力」。其 FORM = 「迴圈工程 ADLC 開發沙盒」。

- **本 repo** = 從 northstar 抽出的 `sandboxes/` 部分（只取完成度高的 3 個），**原樣鏡像（raw mirror）**。
- **只收完成度高的沙盒**：私有 northstar 另有 scope 仍 narrowed 的 `solo-pipeline` 與 `_integration` 整合單元，
  依完成度門檻**未**納入。
- 私有治理層（CLAUDE.md 全文、problem-graph、skills 註冊、`execution/` 腳本、gate 機制）**不在此 repo**。

---

## Sandboxes

**沙盒一覽（3 個全完成單元）**

| 沙盒 | 暴露能力 | `/command` | 一鍵跑綠 | live 能力另需 |
|------|---------|-----------|----------|-------------|
| `openshell-containment` | OpenShell default-deny egress + fs 隔離下的 enforced-containment 執行 + 對抗式 containment_probe（count_metric==0 = 完全 contained） | `/openshell-containment` · `/sandbox-openshell` | ✅ 8 passed | OpenShell + Docker |
| `turbovec` | air-gapped 本地向量檢索——index+self-query 全在 containment 內（count_metric==0 = 不出機器；composes openshell-containment） | `/turbovec` | ✅ 5 passed | 上者 + staged wheels |
| `self-correcting-loop` | PLAN/DO/VERIFY/DECIDE 的確定性 DECIDE 閘——∀criterion ≥ threshold → FINAL，否則 ITERATING + 最弱項；有界 no-progress / exhaustion 守衛；零 LLM-judge | `/self-correcting-loop` | ✅ 25 passed + selftest 6/6 | 無（live 也只需 python3） |

全景圖（機械可驗的 wiring SSOT）：[`sandboxes/PANORAMA.md`](sandboxes/PANORAMA.md)。

---

## Quick verify

**一鍵證明每個沙盒可跑。** clone 後**從 repo 根**跑：

```bash
bash run-tests.sh
# → 3 沙盒的 test 套件 + self-correcting-loop selftest，全綠時 exit 0：
#   self-correcting-loop · selftest ✅ / pytest 25 ✅ · openshell-containment 8 ✅ · turbovec 5 ✅ → ALL GREEN
```

只需 `python3` + `pytest`（`pip install pytest`）——**無** Docker / OpenShell / Ollama（測試把外部邊界 mock 掉）。
每個沙盒因此都有可立即跑綠的入口；下方 [Usage](#usage) 再分（A）當 Claude Code skill 調用、（B）跑底層真實能力。

---

## Usage

**這些 `SKILL.md` 就是 `/command`。** 每個 `sandboxes/<name>/SKILL.md` 是一份**完整的 Claude Code skill 定義**
——frontmatter `name`（= `/command` 名）+ `description`（含觸發詞）+ `allowed-tools`（限定 Bash 權限）+ body 用
`!`cmd`` **dynamic context injection** 在調用時把沙盒當前 runtime 狀態的真 stdout 注入 context。兩條路徑：

### A — 當成 Claude Code skill / `/command` 用

1. **讓 Claude Code 發現它**——把沙盒接成一個 skill：
   ```bash
   mkdir -p ~/.claude/skills/self-correcting-loop
   ln -s "$PWD/sandboxes/self-correcting-loop/SKILL.md" ~/.claude/skills/self-correcting-loop/SKILL.md
   ```
   （或放 project-local 的 `.claude/skills/<name>/SKILL.md`，或在 `settings.json` 把 `sandboxes/` 註冊為 skill 來源。）
   > northstar 沒自動註冊，純粹是它的 settings.json 沒把 `sandboxes/` 列為 skill root，並**另寫** `.claude/commands/<name>.md`
   > 入口控制被動上下文載入——**不是 SKILL.md 不能用**。本 repo 沒附那些入口，所以你自己接。
2. **cwd / 路徑很重要**：SKILL.md 的 `!`cmd`` 注入與 body 用 **repo-relative 路徑**（`sandboxes/<name>/src/...`）。
   調用時 **cwd 要在本 repo 根**，否則注入命令找不到檔；若把 SKILL.md copy 到別處，請同步改 `src/` 路徑。
3. 接好後用 `/<name>` 或觸發詞調用，Claude 依該 SKILL.md body 驅動沙盒。

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
```

---

## Honest boundary

**誠實邊界（什麼能跑、什麼需要設定）：**

- **每個沙盒都可一鍵跑綠**（`bash run-tests.sh`，只需 python3 + pytest，**無** Docker / OpenShell / Ollama）：
  openshell-containment 8 · turbovec 5 · self-correcting-loop 25 passed + selftest 6/6。測試把外部邊界 mock 掉。
- **完整 live 能力**：`self-correcting-loop` 純 python3 即為 live；`openshell-containment`（真實 enforced containment）
  需 OpenShell CLI + Docker；`turbovec`（air-gapped RAG）再加一次性 staged wheels。重型 probe 會寫
  `data/production/...`（northstar 佈局），首次跑可能要先 `mkdir -p`。
- **不隨附的私有件**：`.claude/commands/<name>.md` 入口、共享 gate `fold_in_sandbox_gate.py`、治理詞彙
  （`PG-xxx` / `DDR-031` / `Slop #n` / `engine-locus`）定義——文中對它們、以及對未發佈的 `solo-pipeline` /
  `_integration` 的散文提及是 dangling reference（已知且接受，不是缺檔，別去補）。
- **Zero-API-Key**：常駐檢索 / 嵌入 / rerank 100% 本地化（Ollama），**無雲端 key**。

---

## Absorbed sources (DR)

每個沙盒是把一個外部想法**落地**的結果；那些想法的源頭 Deep Research 報告放在 [`research/`](research/)：

- `openshell-containment` ← 「NVIDIA Open Shell + LangChain Deep Agents 零信任架構」DR
- `turbovec` ← 「embedded 向量資料庫 / turbovec / TurboQuant RAG 重構」DR
- `self-correcting-loop` ← 無 DR（源自使用者 prompt 協定）

> ⚠ DR 是**原始綜述、非 vetted fact**——吸收時的 external-verify 抓出多處 overstated/未查證宣稱
> （詳 [`research/README.md`](research/README.md)）。逐條查證的**裁決帳本（bridge）刻意未公開**（含 northstar
> 內部安全架構）；ZK/KG ingestion 產物亦不公開。

---

## Layout & interface contract

```
adlc-sandboxes/
├── run-tests.sh          ← 一鍵 runnable proof（3 沙盒 test + selftest 全綠）
├── research/             ← 各沙盒吸收的源 DR 報告（raw Gemini DR export，非 vetted fact）
└── sandboxes/
    ├── PANORAMA.md       ← 全景圖（沙盒 wiring 的 live SSOT；機器可解 yaml block）
    └── <name>/
        ├── SKILL.md          ← 沙盒接口契約 = Claude Code skill 定義（frontmatter name = /command 名）
        ├── causal-chain.md   ← 沙盒內技術落地脈絡（外部概念 → bridge → build → 對抗驗證 → 暴露）
        ├── absorption-form.md← 從此沙盒吸收了什麼「形式」
        ├── manifest.yaml     ← 機器可解的能力清單 + 啟動宣告
        └── src/  tests/  trace/
```

接口契約摘要（每個 `SKILL.md` 必滿足）：

- **C1 frontmatter**：`name`（= `/command` 名）/ `description`（含觸發詞）/ `allowed-tools`。
- **C2 ≥1 個 `!`cmd`` 注入**：body 至少一處用 dynamic context injection 把沙盒**當前 runtime 狀態**注入 context（RIP 的接口級實現）。
- **C3 雙因果鏈**：`causal-chain.md`（沙盒內）＋ `absorption-form.md`（吸收形式），兩份分開。
- **C4 全景圖註冊**：在 `PANORAMA.md` 有一 row + 一機器層 yaml block（存在 ≠ 接線，PG-157）。
- **C5 啟動方式分別定義**：frontmatter + manifest 分別宣告 `/command` + 觸發詞 + 啟動前置。

---

## Design invariants

**設計紅線（這套東西的核心約束）：**

- **engine-locus**：自轉只到 SURFACE / VERIFY；**WHAT 由人 admit、DECISION 結果由人接受**，沒有「自動接受結果的飛輪」。
- **確定性閘優於 LLM-judge**：FINAL / contained / air-gapped 這些判定都由確定性 kernel（real scores / exit code /
  count_metric）裁，不是 agent 的散文宣稱。
- **compose 既有層、不造新引擎**：每個沙盒只新增最小的那一塊（如 self-correcting-loop 只新增 DECIDE 閘，
  PLAN/DO/VERIFY 復用既有 loop 層）。

---

## License

MIT — see [`LICENSE`](LICENSE). 涵蓋本 repo 的沙盒代碼與文檔；`research/` 的 DR 是外部研究綜述（raw，非 vetted fact），保留原作脈絡。

---

<div align="center">

*出處：抽取自私有 northstar，僅作技術展示用途。內容語言以中文為主、hero 雙語。*

</div>
