# adlc-sandboxes — 迴圈工程 ADLC 開發沙盒（technical-landing showcase）

> **Raw-mirror showcase.** These are the *technical-landing sandboxes* extracted from a private
> capability-acquisition system (codename **northstar**). Each sandbox is one absorbed concept landed
> as a self-contained mini-project. Each `sandboxes/<name>/SKILL.md` **is a real Claude Code skill /
> `/command` definition** — see [如何使用](#如何使用這些-skillmd-就是-command) below.
>
> Only the **fully-complete (RIP-proven) sandboxes** are published here.

## 這是什麼

- **northstar** = 一套私有的 *demand-pull 能力獲取系統*——把一個外部想法變成 LLM 在 repo 內 runtime
  行為的真實改變，且不把「讀過了 / 長得像」當「長了能力」。其 FORM = 「迴圈工程 ADLC 開發沙盒」。
- **本 repo** = 從 northstar 抽出的 `sandboxes/` 部分（只取完成度高的 3 個），**原樣鏡像（raw mirror）**。
- **只收完成度高的沙盒**：私有 northstar 另有 scope 仍 narrowed 的 `solo-pipeline` 與 `_integration` 整合單元，
  依完成度門檻**未**納入。
- 私有治理層（CLAUDE.md 全文、problem-graph、skills 註冊、`execution/` 腳本、gate 機制）**不在此 repo**。

## 沙盒一覽（3 個全完成單元）

| 沙盒 | 暴露能力 | `/command` | 一鍵跑綠（python3+pytest） | live 能力另需 |
|------|---------|-----------|--------------------------|-------------|
| `openshell-containment` | OpenShell default-deny egress + fs 隔離下的 enforced-containment 執行 + 對抗式 containment_probe（count_metric==0 = 完全 contained） | `/openshell-containment` · `/sandbox-openshell` | ✅ 8 passed | OpenShell + Docker |
| `turbovec` | air-gapped 本地向量檢索——index+self-query 全在 containment 內（count_metric==0 = 不出機器；composes openshell-containment） | `/turbovec` | ✅ 5 passed | 上者 + staged wheels |
| `self-correcting-loop` | PLAN/DO/VERIFY/DECIDE 的確定性 DECIDE 閘——∀criterion ≥ threshold → FINAL，否則 ITERATING + 最弱項；有界 no-progress / exhaustion 守衛；零 LLM-judge | `/self-correcting-loop` | ✅ 25 passed + selftest 6/6 | 無（live 也只需 python3） |

全景圖（機械可驗的 wiring SSOT）：[`sandboxes/PANORAMA.md`](sandboxes/PANORAMA.md)。

## 快速驗證（一鍵，證明每個沙盒可跑）

clone 後**從 repo 根**跑：

```bash
bash run-tests.sh
# → 3 沙盒的 test 套件 + self-correcting-loop selftest，全綠時 exit 0：
#   self-correcting-loop · selftest ✅ / pytest 25 ✅ · openshell-containment 8 ✅ · turbovec 5 ✅ → ALL GREEN
```

只需 `python3` + `pytest`（`pip install pytest`）——**無** Docker / OpenShell / Ollama（測試把外部邊界 mock 掉）。
每個沙盒因此都有可立即跑綠的入口；下方「如何使用」再分（A）當 Claude Code skill 調用、（B）跑底層真實能力。

## 如何使用（這些 `SKILL.md` 就是 `/command`）

每個 `sandboxes/<name>/SKILL.md` 是一份**完整的 Claude Code skill 定義**——frontmatter `name`（= `/command` 名）
+ `description`（含觸發詞）+ `allowed-tools`（限定 Bash 權限）+ body 用 `!`cmd`` **dynamic context injection** 在調用時
把沙盒當前 runtime 狀態的真 stdout 注入 context。有兩條使用路徑：

### A. 當成 Claude Code skill / `/command` 用

1. **讓 Claude Code 發現它**——把沙盒接成一個 skill：
   - 最簡單（symlink 進你的 skills 目錄）：
     `mkdir -p ~/.claude/skills/self-correcting-loop && ln -s "$PWD/sandboxes/self-correcting-loop/SKILL.md" ~/.claude/skills/self-correcting-loop/SKILL.md`
     （或放 project-local 的 `.claude/skills/<name>/SKILL.md`。）
   - 或在你的 `settings.json` 把本 repo 的 `sandboxes/` 註冊為 skill 來源。
   > northstar 沒自動註冊，純粹是它的 settings.json 沒把 `sandboxes/` 列為 skill root，並**另寫** `.claude/commands/<name>.md`
   > 入口來控制被動上下文載入——**不是 SKILL.md 不能用**。本 repo 沒附那些 `.claude/commands/` 入口，所以你自己接。
2. **cwd / 路徑很重要**：SKILL.md 裡的 `!`cmd`` 注入與 body 用的是 **repo-relative 路徑**（`sandboxes/<name>/src/...`）。
   調用時 **cwd 要在本 repo 根目錄**，否則注入命令找不到檔；若把 SKILL.md copy 到別處，請同步改 `src/` 路徑。
3. 接好後用 `/<name>` 或觸發詞調用，Claude 依該 SKILL.md body 驅動沙盒（先跑 `!`cmd`` 注入即時狀態，再依「能力與調用」段執行）。

### B. 直接跑底層能力（不需 Claude Code）

每個沙盒的真實邏輯在 `src/`；manifest 的 `runtime_trace_cmd` 是正規自驗調用。**從 repo 根目錄**跑：

```bash
# self-correcting-loop — 純 python3，立即可跑（已驗 selftest 6/6 PASS）
(cd sandboxes/self-correcting-loop && python3 src/loop_kernel.py selftest --iso 2026-06-23)

# 一輪實際用法：LLM 產出 artifact + 對 rubric 評分寫成 scorecard JSON，kernel 確定性裁決：
(cd sandboxes/self-correcting-loop && \
  python3 src/loop_kernel.py decide \
    --rubric src/fixtures/rubric.json \
    --scorecard src/fixtures/scorecard-final.json \
    --loop demo --iso 2026-06-23)
# → FINAL(exit 0) iff 每條 criterion ≥ threshold；否則 ITERATING(exit 3) + 最弱失敗項 + 推進 loop-state
#    （no-progress / exhausted → SURFACE 交人，不自動續跑）

# openshell-containment — 需先裝 OpenShell CLI + Docker
bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status   # 非 Connected →
bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh up --sandbox ns-sandbox
python3 sandboxes/openshell-containment/src/containment_probe.py --iso 2026-06-23

# turbovec — 需 openshell-containment 就緒 + 一次性 stage 離線 wheel
bash sandboxes/turbovec/src/stage_turbovec_wheels.sh
python3 sandboxes/turbovec/src/containment_rag_probe.py -n ns-sandbox
```

> 各沙盒自己的測試也可直接跑：`python3 -m pytest sandboxes/<name>/tests/`（多為確定性）。

## ⚠ 誠實邊界（什麼能跑、什麼需要設定）

- **每個沙盒都可一鍵跑綠**（`bash run-tests.sh`，只需 python3 + pytest，**無** Docker / OpenShell / Ollama）：
  openshell-containment 8 · turbovec 5 · self-correcting-loop 25 passed + selftest 6/6。測試把外部邊界 mock 掉。
- **完整 live 能力**：`self-correcting-loop` 純 python3 即為 live；`openshell-containment`（真實 enforced containment）
  需 OpenShell CLI + Docker；`turbovec`（air-gapped RAG）再加一次性 staged wheels。重型 probe 會寫
  `data/production/...`（northstar 佈局），首次跑可能要先 `mkdir -p` 該輸出目錄。
- **不隨附的私有件**：`.claude/commands/<name>.md` 入口、共享 gate `fold_in_sandbox_gate.py`、治理詞彙
  （`PG-xxx` / `DDR-031` / `Slop #n` / `engine-locus`）定義——文中對它們、以及對未發佈的 `solo-pipeline` /
  `_integration` 的散文提及是 dangling reference（已知且接受，不是缺檔，別去補）。
- **Zero-API-Key**：常駐檢索 / 嵌入 / rerank 100% 本地化（Ollama），**無雲端 key**。

## 每個 `sandboxes/<name>/` 的 layout + 接口契約

```
sandboxes/<name>/
  SKILL.md          ← 沙盒接口契約 = Claude Code skill 定義（C1–C5；frontmatter name = /command 名）
  causal-chain.md   ← 沙盒內技術落地脈絡（外部概念 → bridge → build → 對抗驗證 → 暴露）
  absorption-form.md← 從此沙盒吸收了什麼「形式」（pruning verdict / cut_class / runtime_comparison）
  manifest.yaml     ← 機器可解的暴露能力清單 + 啟動宣告（command / triggers / precondition / runtime_trace_cmd）
  src/              ← 沙盒真實能力源碼
  tests/            ← 沙盒自身 runtime 測試（gate 問答層 + runtime-trace 層消費）
  trace/            ← runtime trace 落點（真調用 exit code 記錄 + fold-in-gate.record.json）
```

接口契約摘要（每個 `SKILL.md` 必滿足）：
- **C1 frontmatter**：`name`（= `/command` 名）/ `description`（含觸發詞）/ `allowed-tools`。
- **C2 ≥1 個 `!`cmd`` 注入**：body 至少一處用 dynamic context injection 把沙盒**當前 runtime 狀態**注入 context（RIP 的接口級實現）。
- **C3 雙因果鏈**：`causal-chain.md`（沙盒內）＋ `absorption-form.md`（吸收形式），兩份分開。
- **C4 全景圖註冊**：在 `PANORAMA.md` 有一 row + 一機器層 yaml block（存在 ≠ 接線，PG-157）。
- **C5 啟動方式分別定義**：frontmatter + manifest 分別宣告 `/command` + 觸發詞 + 啟動前置。

## 設計紅線（這套東西的核心約束）

- **engine-locus**：自轉只到 SURFACE / VERIFY；**WHAT 由人 admit、DECISION 結果由人接受**，沒有「自動接受結果的飛輪」。
- **確定性閘優於 LLM-judge**：FINAL / contained / air-gapped 這些判定都由確定性 kernel（real scores / exit code /
  count_metric）裁，不是 agent 的散文宣稱。
- **compose 既有層、不造新引擎**：每個沙盒只新增最小的那一塊（如 self-correcting-loop 只新增 DECIDE 閘，
  PLAN/DO/VERIFY 復用既有 loop 層）。

---

*出處：抽取自私有 northstar，僅作技術展示用途。內容語言以中文為主。*
