# DR → RUN 對應圖：哪些 DR 願景「跑 `/command` 就真兌現」

> 這份檔把 [`research/`](.) 的兩份 **raw Deep Research 報告**（願景、宣稱、未查證的綜述）連到
> 各沙盒 [`RUN.md`](../sandboxes) 的**真實 live 結果**，並明確標出每條 DR 敘述屬於哪一類：
>
> - **✅ 跑 `/command` 即真實達成/復現** — DR 這段被沙盒落地 + 對抗驗證，執行對應 `/command` 能親眼驗證。
> - **⚠ 只落地一部分** — DR 講的更大，沙盒只兌現了其中可確定性驗證的那塊（誠實邊界）。
> - **❌ DR 講了但 `/command` 不驗證 / 吸收時已裁** — 範圍外，或 external-verify 抓出的 overstated 宣稱。
>
> **核心結論先講**：DR 用大篇幅描繪完整願景（Model + Harness + Observability + 端到端氣隙 RAG + drop-in
> 生態），但**跑 `/command` 能真兌現的只有「Runtime 容管」那一小塊**。這正是沙盒「compose 既有層、
> 只落地能對抗驗證的最小那塊」的紀律——DR 是**原始綜述、非 vetted fact**（見 [`README.md`](README.md)）。

---

## openshell-containment ← 零信任 DR

源 DR：[`自主代理技術的解耦與重構…零信任架構深度研究報告.md`](<自主代理技術的解耦與重構：基於 NVIDIA Open Shell 安全執行期與 LangChain Deep Agents 的零信任架構深度研究報告.md>)
· 落地產物：[`sandboxes/openshell-containment/RUN.md`](../sandboxes/openshell-containment/RUN.md)
· 入口：[`/sandbox-openshell`](../.claude/commands/sandbox-openshell.md)

### ✅ 跑 `/sandbox-openshell --probe` 即真實達成/復現

| DR 章節 | DR 原文敘述 | RUN.md 跑出的證據 |
|---|---|---|
| **S2 零信任網路阻斷**（§零信任治理） | 「在 OS **內核/網卡層級**強制出站規則，非代碼層面；非白名單域名 → 網路驅動層**直接拒絕發包**」 | `egress_exfil_blocked: contained` — `curl: (56) CONNECT tunnel failed, response 403` |
| **D3.2 evil.com 阻斷實錄**（§終端執行追蹤） | 「注入發 POST 到 evil.com → Open Shell **L7 政策引擎內核層攔截 403**」 | 同一條 egress case（probe 打非白名單 host → 403/curl56），該 case `failure=0` |
| **S1 目錄穿越防護**（§零信任治理） | 「**嚴禁沙盒進程訪問** `/host/etc` 或**用戶根目錄**；Landlock 唯讀」 | `fs_host_home_isolated: contained` — `ls /Users` → `No such file or directory` |
| **執行期容管法則·Runtime 行**（§組件矩陣） | 「NVIDIA Open Shell：進程/文件/**網路**/推理**四層隔離**，Landlock + seccomp」 | `containment_probe cases=3 failures=0`（網路 + 文件兩層真驗 + legit `/sandbox` write OK） |

**復現**：`python3 sandboxes/openshell-containment/src/containment_probe.py --iso <ISO> -n ns-sandbox`
（需 OpenShell gateway 就緒；`count_metric==0` = 上面四條全綠）。

### ❌ DR 講了但 `/command` 不驗證（沙盒範圍外）

- **隱私路由器**（`inference.local` 在網閘注入 API key，使沙盒接觸不到真實密鑰）— 沙盒未測此路徑。
- **跨沙盒記憶持久化**（D3.3：`agent.md` 映射宿主硬碟）— 未驗。
- **LangChain Deep Agents 中間件**（SummarizationMiddleware / Patch Tool Calls 自我修正）、**NeMoTron 3 Model**、
  **LangSmith 可觀測性** — 這些是 Harness / Model / Observability 層，**不在 Runtime-containment 沙盒範圍**。

---

## turbovec ← embedded-vector DR

源 DR：[`嵌入式向量資料庫的技術演進…RAG 重構分析.md`](<嵌入式向量資料庫的技術演進與策略變革：以 turbovec 及 TurboQuant 演算法為核心的 RAG 重構分析.md>)
· 落地產物：[`sandboxes/turbovec/RUN.md`](../sandboxes/turbovec/RUN.md)
· 入口：[`/turbovec`](../.claude/commands/turbovec.md)

### ✅ 跑 `/turbovec` 即真實達成/驗證

| DR 章節 | DR 原文敘述 | RUN.md 跑出的證據 |
|---|---|---|
| **完全本地氣隙 RAG**（§完全本地氣隙 RAG 與生態系整合實務） | 「完全物理隔離、無數據外洩、**100% 氣隙（Air-gapped）的安全 RAG 系統**」 | `containment_rag_probe count_metric=0`：ns-sandbox 內 `recall_at1=1.0` **∧** egress 拒（curl56/403）= air-gapped 機器證明 |
| **典範轉移：雲端 → 嵌入式 pip 庫**（§向量檢索的典範轉移） | 「向量 DB 從雲端託管變 **embedded `pip install` 函式庫**」 | turbovec offline abi3 wheel staged 進 ns-sandbox（`stage_turbovec_wheels.sh`），**無網路**可 import + 跑 |

**復現**：`python3 sandboxes/turbovec/src/containment_rag_probe.py -n ns-sandbox`
（需 openshell-containment 就緒 + turbovec 已 staged；`count_metric==0` = 檢索能跑 **∧** egress 被拒）。

### ⚠ 只落地「檢索層」（誠實邊界）

`/turbovec` 驗的是 turbovec **index 在氣隙內可跑**（deterministic seeded 向量）。DR 的「Ollama BGE-M3 +
本地 LLM **端到端**氣隙 RAG」只落地了**檢索層**——嵌入（Ollama）與生成（本地 LLM）那兩段**不在**沙盒驗證範圍。
氣隙的**邊界**由 openshell-containment 的 default-deny egress 保證（turbovec compose 它），不是 turbovec 自帶。

### ❌ DR 講了但 `/command` 不驗證 / 吸收時已裁（external-verify 抓的 overstated）

- **壓縮比「8–16 倍 / 31GB→4GB」**：external-verify + 對真實 embeddings 的 runtime-trace 顯示 **16× 是 2-bit
  檔位（recall 崩到 min ~0.60）**，4-bit 實測僅 **~7.9×**（recall@10 ~0.957）。`/turbovec` 用 `dim=64` 的小集，
  **未驗**千萬級壓縮比——DR 的「塞進 MacBook」是**最佳檔位的數字**，非 recall 可用檔位。
- **Drop-in Replacement（LangChain / LlamaIndex / Haystack / Agno「一行替換」）**：**未落地**，且吸收時裁定為
  **範疇錯誤**——turbovec 是向量 **INDEX**（dense kNN + id-allowlist），而生產級消費面要的是向量 **DATABASE**
  （metadata where-filter / 多 collection / 多進程）；「drop-in」被重標為 *scoped single-collection backend
  swap（demand-gated, default-off）*。
- **TurboQuant 數學機制 / TQ+ 校準**、**基準召回率 benchmark 具體數字** — `/command` 不驗證（probe 驗的是
  seeded `recall=1.0`，非 DR 引用的真實 benchmark）。

---

## self-correcting-loop — 無 DR

`self-correcting-loop` **不源自 DR**，而是源自使用者直接給的 PLAN/DO/VERIFY/DECIDE 迴圈協定，故不在本對應圖內。
它執行 [`/self-correcting-loop`](../.claude/commands/self-correcting-loop.md) 達成的是**那個協定**（確定性 DECIDE 閘），
真實結果見 [`sandboxes/self-correcting-loop/RUN.md`](../sandboxes/self-correcting-loop/RUN.md)。

---

*邊界誠實聲明：本檔的「DR 原文敘述」是綜述引用、非已查證事實；「❌ / ⚠」欄是吸收時 external-verify 的裁定。
逐條查證的完整核對過程不在本檔——這裡只呈現「落地 vs 宣稱」的邊界結論。*
