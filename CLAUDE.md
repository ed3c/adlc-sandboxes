# CLAUDE.md — adlc-sandboxes

> 給在這個 repo 裡工作的 agent / 讀者的指令。本 repo = 三個自洽的小沙盒，每個把一個外部想法落地成
> 一個可運行、確定性驗證的能力，並以 Claude Code `/command` 暴露。完整背景見 [`README.md`](README.md)。

## 這個 repo 的性質（先讀這段）

- **每個沙盒都可一鍵跑綠**：`bash run-tests.sh`（只需 python3 + pytest，無 Docker / OpenShell / Ollama；
  測試把外部邊界 mock 掉）。`src/` + `tests/` 是真實自洽代碼，可單獨閱讀、運行、改造。
- **`/command` 入口已隨附**：`.claude/commands/`（`self-correcting-loop.md` · `sandbox-openshell.md` ·
  `turbovec.md`；`/turbovec` compose openshell-containment，入口先確認 gateway + staged 前置）。clone 後把本
  repo 當 project 開（cwd 在 repo 根）即可調用。
- **完整 live 能力分兩種**：`self-correcting-loop` 純 python3 即 live；`openshell-containment` /
  `turbovec` 的真實 containment / air-gapped RAG 另需 OpenShell CLI + Docker（+ staged wheels）。
  各沙盒真實運作與生產消費關係見各 `RUN.md` + 頂層 `PRODUCTION-CONSUMPTION.md`。

## 結構

```
README.md                 ← 公開說明（沙盒一覽 + 如何使用 + 誠實邊界）
CLAUDE.md                 ← 本檔
run-tests.sh              ← 一鍵 runnable proof（3 沙盒 test + selftest 全綠）
PRODUCTION-CONSUMPTION.md ← 沙盒在 Claude Code 的生產消費關係（總覽）
.claude/commands/         ← /command 入口（self-correcting-loop.md · sandbox-openshell.md · turbovec.md）
research/                 ← 各沙盒吸收的源 DR 報告（raw Gemini DR export，非 vetted fact）
sandboxes/
  PANORAMA.md             ← 全景圖（沙盒 wiring 的 live 真相；機器可解 yaml block）
  <name>/
    SKILL.md              ← 沙盒接口契約 = Claude Code skill 定義（frontmatter name = /command 名）
    RUN.md               ← 實際運作過程與結果（生產消費循環 + 真實 live transcript）
    manifest.yaml         ← 機器可解的能力清單 + 啟動宣告
    src/  tests/  trace/
```

## 在這個 repo 裡可以做 / 不要做

- ✅ 讀懂某沙盒的設計：先 `manifest.yaml` → `SKILL.md` → `RUN.md` → `src/`。
- ✅ `bash run-tests.sh` 一鍵驗證每個沙盒可跑；或跑單一沙盒 `tests/`。
- ✅ 把某個沙盒的 `src/` 抽出來改造成你自己的東西。
- ✅ 把 `SKILL.md` 接成 Claude Code skill 用 `/<name>` 調用（見 README「Usage」；cwd 須在 repo 根）。
- ❌ 不要把 `research/` 的 DR 當查證事實——它是**原始綜述**，吸收時抓出多處 overstated / 未查證宣稱（詳 `research/README.md`）。
- ❌ 不要修改 `src/` / `tests/` 的測試期望來「讓它通過」——runtime 綠是唯一完成判據。

## 設計哲學（理解這些才看得懂沙盒）

- **確定性閘優於 LLM-judge**：FINAL / contained / air-gapped 由確定性 kernel（real scores / exit code /
  `count_metric`）裁，不靠 agent 散文宣稱。
- **compose 既有層、不造新引擎**：每個沙盒只新增最小那一塊（如 self-correcting-loop 只新增 DECIDE 閘）。
- **人決定 WHAT、人接受結果**：沒有自動接受結果、自動續跑的循環；沙盒只跑確定性那一步。
- **誠實邊界**：能力宣稱要有硬數據；`MagicMock` 只證介面連通不證 runtime 行為。
