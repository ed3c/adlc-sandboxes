# adlc-sandboxes — 迴圈工程 ADLC 開發沙盒（technical-landing showcase）

> **Raw-mirror showcase.** These are the *technical-landing sandboxes* extracted from a private
> capability-acquisition system (codename **northstar**). Each sandbox is one absorbed concept
> landed as a self-contained mini-project. This repo is for **reading / studying**, not for running
> the full governed loop — the orchestration layer is private (see the honest boundary below).
>
> Only the **fully-complete (RIP-proven) sandboxes** are published here.

## 這是什麼

- **northstar** = 一套私有的 *demand-pull 能力獲取系統*——把一個外部想法變成 LLM 在 repo 內 runtime
  行為的真實改變，且不把「讀過了 / 長得像」當「長了能力」。其 FORM = 「迴圈工程 ADLC 開發沙盒」。
- **本 repo** = 從 northstar 抽出的 `sandboxes/` 部分，**原樣鏡像（raw mirror）**，作為技術落地的公開展示。
- **只收完成度高的沙盒**：私有 northstar 另有 scope 仍 narrowed 的 `solo-pipeline` 與 `_integration` 整合單元，
  依完成度門檻**未**納入本鏡像。
- 私有治理層（CLAUDE.md 全文、problem-graph、skills 註冊、`execution/` 腳本、gate 機制）**不在此 repo**。

## ⚠ 誠實邊界（這個 repo 不能直接跑）

原樣鏡像保留了對私有 northstar 的引用。缺下列私有件，故 **as-is 跑不起來**，定位是「展示 / 閱讀」**非**「可獨立運行」：

1. **可調用入口** `.claude/commands/<name>.md`——每個沙盒的 `/command` 真正 entry，**不在 `sandboxes/` 內**
   （`sandboxes/` 非 skill root，`SKILL.md` 不會自動註冊 `/command`）。
2. **共享 gate** `execution/scripts/fold_in_sandbox_gate.py`——四層 fold-in 驗證閘（static / qa / runtime / composition）。
3. **治理詞彙定義**——文中出現的 `PG-xxx`、`DDR-031`、`Slop #n`、`ADR-000x`、`engine-locus` 等 token，
   定義都在私有 northstar，這裡是 dangling reference（包含對未發佈的 `solo-pipeline` / `_integration` 的散文提及）。

不過——每個沙盒 `src/` + `tests/` 是**自洽的真實代碼**，可單獨閱讀 / 改造。多數只依賴 `python3` / `node` /
本地 `Ollama` / `Docker`，**無雲端 API key**（Zero-API-Key 原則：常駐檢索/嵌入/rerank 100% 本地化）。

## 沙盒一覽（3 個全完成單元）

| 沙盒 | 暴露能力 | 入口 | wiring |
|------|---------|------|--------|
| `openshell-containment` | OpenShell default-deny egress + fs 隔離下的 enforced-containment 執行 + 對抗式 containment_probe（count_metric==0 = 完全 contained） | `/sandbox-openshell` | LIVE |
| `turbovec` | air-gapped 本地向量檢索——index+self-query 全在 containment 內（count_metric==0 = 不出機器；composes openshell-containment） | `/turbovec` | LIVE |
| `self-correcting-loop` | PLAN/DO/VERIFY/DECIDE 的確定性 DECIDE 閘——∀criterion ≥ threshold → FINAL，否則 ITERATING + 最弱項；有界 no-progress / exhaustion 守衛；零 LLM-judge | `/self-correcting-loop` | LIVE |

全景圖（機械可驗的 wiring SSOT）：[`sandboxes/PANORAMA.md`](sandboxes/PANORAMA.md)。

## 每個 `sandboxes/<name>/` 的 layout + 接口契約

```
sandboxes/<name>/
  SKILL.md          ← 沙盒接口契約文件（C1–C5；被私有 gate 機械驗，非自動註冊的 command）
  causal-chain.md   ← 沙盒內技術落地脈絡（外部概念 → bridge → build → 對抗驗證 → 暴露）
  absorption-form.md← 從此沙盒吸收了什麼「形式」（pruning verdict / cut_class / runtime_comparison）
  manifest.yaml     ← 機器可解的暴露能力清單 + 啟動宣告（command / triggers / precondition）
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
