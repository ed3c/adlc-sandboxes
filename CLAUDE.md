# CLAUDE.md — adlc-sandboxes（公開鏡像 repo）

> 給在這個 repo 裡工作的 agent / 讀者的指令。本 repo = 私有系統 **northstar** 的 `sandboxes/` 部分（只取
> 完成度高的 3 個沙盒）的**原樣鏡像（raw mirror）**，定位是技術落地的**公開展示**，不是可獨立運行的活系統。
> 完整背景見 [`README.md`](README.md)。

## 這個 repo 的性質（先讀這段）

- **唯讀為主的展示鏡像**：內容從 northstar 抽出，原樣保留。不要試圖在這裡「接線成活系統」——
  orchestration / gate / `/command` 註冊那套機制在私有 northstar，**不在此 repo**。
- **跑不起來是預期的**（指 live 能力）：每個沙盒的 `/command` 入口（`.claude/commands/<name>.md`）、共享 gate
  （`fold_in_sandbox_gate.py`）、治理詞彙定義（`PG-xxx` / `DDR-031` / `Slop #n` / `engine-locus`）都**缺**。
  文中對它們、以及對未發佈的 `solo-pipeline` / `_integration` 的散文提及，都是 dangling reference，
  **這是已知且接受的**，不是 bug、不要「修」它們。但**每個沙盒都有可一鍵跑綠的 test 入口**（見 README「快速驗證」）。
- **`src/` + `tests/` 是真實自洽代碼**：可單獨閱讀、`bash run-tests.sh` 一鍵跑綠（只需 python3+pytest）、改造。

## 結構

```
README.md            ← 公開說明（沙盒一覽 + 如何使用 + 誠實邊界 + 接口契約摘要）
CLAUDE.md            ← 本檔
run-tests.sh         ← 一鍵 runnable proof（3 沙盒 test + selftest 全綠）
sandboxes/
  PANORAMA.md        ← 全景圖（沙盒 wiring 的 live SSOT；機器可解 yaml block）
  openshell-containment/
  turbovec/
  self-correcting-loop/
    SKILL.md         ← 沙盒接口契約 = Claude Code skill 定義（被私有 gate 機械驗；frontmatter name = /command 名）
    causal-chain.md  ← 沙盒內技術落地脈絡
    absorption-form.md ← 吸收了什麼「形式」
    manifest.yaml    ← 機器可解的能力清單 + 啟動宣告
    src/  tests/  trace/
research/            ← 各沙盒吸收的源 DR 報告（raw Gemini DR export，非 vetted fact）
```

## 在這個 repo 裡可以做 / 不要做

- ✅ 讀懂某沙盒的設計：先 `manifest.yaml` → `SKILL.md` → `causal-chain.md` → `src/`。
- ✅ `bash run-tests.sh` 一鍵驗證每個沙盒可跑；或跑單一沙盒 `tests/`。
- ✅ 把某個沙盒的 `src/` 抽出來改造成你自己的東西。
- ✅ 把 `SKILL.md` 接成 Claude Code skill 用 `/<name>` 調用（見 README「如何使用」；cwd 須在 repo 根）。
- ❌ 不要為了「讓它能跑」而去重建私有 gate / `/command` / 治理層——那超出本鏡像範圍。
- ❌ 不要把 dangling 的 `PG-xxx` / `DDR` / `ADR` / `solo-pipeline` / `_integration` 引用當成缺失檔去補。
- ❌ 不要把 `research/` 的 DR 當查證事實——它是**原始綜述**，吸收時抓出多處 overstated/未查證宣稱，
  逐條查證的裁決帳本（bridge）刻意未公開。
- ❌ 不要把這份鏡像當成 northstar 的真相來源——真相在私有 repo；這裡是某時點的快照。

## 設計哲學（沿用自 northstar，理解這些才看得懂沙盒）

- **engine-locus**：自轉只到 SURFACE / VERIFY；WHAT 由人 admit、結果由人接受。沒有自動接受結果的飛輪。
- **確定性閘優於 LLM-judge**：FINAL / contained / air-gapped 由確定性 kernel（real scores / exit code /
  `count_metric`）裁，不靠 agent 散文宣稱。
- **compose 既有層、不造新引擎**：每個沙盒只新增最小那一塊。
- **誠實邊界（Slop #18）**：能力宣稱要有硬數據；`MagicMock` 只證介面連通不證 runtime 行為。
