# CLAUDE.md — adlc-sandboxes（公開鏡像 repo）

> 給在這個 repo 裡工作的 agent / 讀者的指令。本 repo = 私有系統 **northstar** 的 `sandboxes/` 部分（只取
> 完成度高的 3 個沙盒）的**原樣鏡像（raw mirror）**，定位是技術落地的**公開展示**，不是可獨立運行的活系統。
> 完整背景見 [`README.md`](README.md)。

## 這個 repo 的性質（先讀這段）

- **唯讀為主的展示鏡像**：內容從 northstar 抽出，原樣保留。不要試圖在這裡「接線成活系統」——
  orchestration / gate / `/command` 註冊那套機制在私有 northstar，**不在此 repo**。
- **跑不起來是預期的**：每個沙盒的 `/command` 入口（`.claude/commands/<name>.md`）、共享 gate
  （`fold_in_sandbox_gate.py`）、治理詞彙定義（`PG-xxx` / `DDR-031` / `Slop #n` / `engine-locus`）都**缺**。
  文中對它們、以及對未發佈的 `solo-pipeline` / `_integration` 的散文提及，都是 dangling reference，
  **這是已知且接受的**，不是 bug、不要「修」它們。
- **`src/` + `tests/` 是真實自洽代碼**：可單獨閱讀、運行各沙盒自己的 `tests/`、改造。多依賴 `python3` /
  `node` / 本地 `Ollama` / `Docker`，無雲端 key。

## 結構

```
README.md            ← 公開說明（沙盒一覽 + 誠實邊界 + 接口契約摘要）
CLAUDE.md            ← 本檔
sandboxes/
  PANORAMA.md        ← 全景圖（沙盒 wiring 的 live SSOT；機器可解 yaml block）
  openshell-containment/
  turbovec/
  self-correcting-loop/
    SKILL.md         ← 沙盒接口契約文件（被私有 gate 機械驗；非自動註冊的 command）
    causal-chain.md  ← 沙盒內技術落地脈絡
    absorption-form.md ← 吸收了什麼「形式」
    manifest.yaml    ← 機器可解的能力清單 + 啟動宣告
    src/  tests/  trace/
```

## 在這個 repo 裡可以做 / 不要做

- ✅ 讀懂某沙盒的設計：先 `manifest.yaml` → `SKILL.md` → `causal-chain.md` → `src/`。
- ✅ 跑單一沙盒自己的 `tests/`（多為純 python / 確定性）。
- ✅ 把某個沙盒的 `src/` 抽出來改造成你自己的東西。
- ❌ 不要為了「讓它能跑」而去重建私有 gate / `/command` / 治理層——那超出本鏡像範圍。
- ❌ 不要把 dangling 的 `PG-xxx` / `DDR` / `ADR` / `solo-pipeline` / `_integration` 引用當成缺失檔去補。
- ❌ 不要把這份鏡像當成 northstar 的真相來源——真相在私有 repo；這裡是某時點的快照。

## 設計哲學（沿用自 northstar，理解這些才看得懂沙盒）

- **engine-locus**：自轉只到 SURFACE / VERIFY；WHAT 由人 admit、結果由人接受。沒有自動接受結果的飛輪。
- **確定性閘優於 LLM-judge**：FINAL / contained / air-gapped 由確定性 kernel（real scores / exit code /
  `count_metric`）裁，不靠 agent 散文宣稱。
- **compose 既有層、不造新引擎**：每個沙盒只新增最小那一塊。
- **誠實邊界（Slop #18）**：能力宣稱要有硬數據；`MagicMock` 只證介面連通不證 runtime 行為。
