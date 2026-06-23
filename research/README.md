# research/ — 各沙盒吸收的源 Deep Research 報告（DR）

> 這些是 `sandboxes/` 吸收的**外部想法源頭**（Gemini Deep Research 匯出），放這裡讓技術落地的 provenance
> 完整：**DR（外部想法）→ sandbox（落地）**。

## DR ↔ 沙盒對應

| DR | 對應沙盒 | 核心 thesis |
|----|---------|-------------|
| 自主代理技術的解耦與重構…NVIDIA Open Shell…零信任架構深度研究報告 | [`openshell-containment`](../sandboxes/openshell-containment/) | Model/Runtime/Harness 三層解耦 + zero-trust 執行期容管（blast-radius ∝ Runtime 權限、⊥ Model alignment） |
| 嵌入式向量資料庫的技術演進…turbovec / TurboQuant…RAG 重構分析 | [`turbovec`](../sandboxes/turbovec/) | 向量資料庫去中心化為 embedded `pip install` + air-gapped 本地 RAG |

`self-correcting-loop` **無對應 DR**——它的外部概念來自使用者的 prompt 協定（PLAN/DO/VERIFY/DECIDE 四步），非一份 DR。

## ⚠ 誠實邊界（重要 — 別把 DR 當事實）

- 這些是**原始 DR 綜述**（raw Gemini DR export），**不是經查證的事實**。落地吸收時對它們做過 external-verify
  （stealth-fetch 各自 bibliography 的 primary），抓出多處 **overstated / 未查證**的宣稱：
  - openshell DR 把 NVIDIA OpenShell 框成「生產級 / 自主進化」——其 primary README 自陳 **alpha / single-player /
    proof-of-life / human-gated**；`openshell gateway start` 指令在 v0.0.59 根本不存在；「PocketOS 9 秒刪庫 /
    30 秒主機被控」「Open Claw 十萬星、中國禁用、微軟 Scout」屬敘事鋪陳，非全可考。
  - turbovec DR 的「比 FAISS 快 / 接近香農極限 / TurboQuant 驅動 H100 8×」——primary 證實多為 **UNVERIFIED**
    或反向（x86 2-bit 反而慢 ~8%；實為香農下界 2.7×）。
- 請把這兩份 DR 當**原始吸收輸入**讀，**不是 vetted fact**——沙盒落地的是「形式 / 能力」，不是 DR 的每句宣稱。
- turbovec DR 的公式/數字以 **base64-PNG 內嵌**（Gemini DR 匯出特性），在 GitHub 上會 render 成圖。
- 原檔名保留（Gemini Deep Research 匯出）。
