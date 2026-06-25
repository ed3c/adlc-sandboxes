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

## arch-fitness ← 軟體架構戰略/戰術 DR

源 DR：[`軟體架構的戰略與戰術雙重奏…系統性研究.md`](<軟體架構的戰略與戰術雙重奏：從領域邊界劃分到代碼演進治理的系統性研究.md>)
· 落地產物：[`sandboxes/arch-fitness/RUN.md`](../sandboxes/arch-fitness/RUN.md)
· 入口：[`/arch-fitness`](../.claude/commands/arch-fitness.md)（或直接跑 `sandboxes/arch-fitness/src/arch_fitness_kernel.py`）

### ✅ 跑 `arch_fitness_kernel.py measure` 即真實達成/復現

| DR 章節 | DR 原文敘述 | RUN.md 跑出的證據 |
|---|---|---|
| **戰略：領域邊界 / 分層** | 「Clean Architecture 分層依賴規則——內層不得依賴外層；模組化單體的 module-boundary 白名單」 | `measure` 對 sample_project → `verdict=FAIL`、`layer_violations`（controllers→persistence）+ `boundary_violations`（controllers↑persistence、workflow↑controllers），確定性、含 file:lineno |
| **戰略：耦合度量（Martin metrics）** | 「以 Instability(I) / Abstractness(A) / Distance(D) 量耦合，標出 Zone of Pain」 | report 的 `coupling` 段印每元件 ca/ce/I/A/D；Zone-of-Pain **surfaced 非 gated**（誠實邊界） |
| **戰術：代碼演進壞味道** | 「Long Method / Too Many Parameters / Large Class 等可 AST 量測的壞味道」 | selftest `long_method_detected` / `too_many_params_detected` / `large_class_detected` 全 PASS（AST 量測） |
| **作為 evals 標準導引迴圈** | 「fitness function 應持續量測架構是否隨演進腐化，導引修復」 | `rubric`（三軸）+ `scorecard` 投影成 `self-correcting-loop` 可消費的 runnable scorecard；`focus`=最弱維導下一輪 |

### ⚠ 只落地「結構量測」那塊（誠實邊界）

- arch-fitness 量的是**結構**（layer/boundary/coupling + AST 壞味道）；DR 講的「代碼演進**治理**」更大（重構排程、團隊流程、遷移策略）——`/command` 不驗證那些。
- 3 個 `semantic` 維度（module_depth / self-documenting / errors-out-of-existence）**非機器可量**——留在 loop 的 LLM-VERIFY，非 kernel 裁（anti placebo-fitness）。

### ❌ DR 講了但 `arch_fitness_kernel.py` 不驗證

- **DDD 戰略設計**（bounded context 劃分、context map、ubiquitous language）— 範圍外，沙盒不替你劃領域。
- **重構迴圈的執行**（per-function 機械重構）= 另一軸（`/refactor-loop`），arch-fitness 只 DIRECT（指 WHERE），不 wire HOW。

---

## capacity-estimation ← AI-Agent 容量估算 DR

源 DR：[`AI Agent 時代的計算系統容量估算與架構設計研究報告.md`](<AI Agent 時代的計算系統容量估算與架構設計研究報告.md>)
· 落地產物：[`sandboxes/capacity-estimation/RUN.md`](../sandboxes/capacity-estimation/RUN.md)
· 入口：[`/capacity-estimation`](../.claude/commands/capacity-estimation.md)（或直接跑 `sandboxes/capacity-estimation/src/capacity_kernel.py`）

### ✅ 跑 `capacity_kernel.py estimate/judge` 即真實復現

| DR 章節 | DR 原文敘述 | RUN.md 跑出的證據 |
|---|---|---|
| **§2 代理放大 / 吞吐** | 「Agent 把 1 個用戶請求放大成 N 次 LLM 調用；估 QPS / token TPS」 | estimate 的 DR 範例 → `agent_qps=40`, `total_tps=140000`（忠實複現 DR worked example） |
| **§3 顯存 = 權重 + KV** | 「VRAM = 模型權重 + KV cache；KV/token = 2·layers·hidden·2bytes」 | `kv_per_token_bytes=327680`(exact), `weights gb=140`, `total_vram gb=182.95`, `cards_needed=3`（80GB 卡） |
| **§5 架構檢核表 → 可行性** | 「對照預算逐項檢核，標出不可行的綁定約束 + 對應架構/代碼槓桿」 | judge exit 0/3；INFEASIBLE 時逐綁定帶 macro lever（卡/TP/RAM）+ micro lever（FP8 KV / PagedAttention …） |
| **RAG 記憶 RAM** | 「向量庫 RAM = raw + index 開銷（HNSW ~1.8×）」 | `rag raw gb=122.88`, `with_index gb=184.32`, 推薦 index 隨 recall/latency 需求切換 |

### ⚠ 只落地「估算 + 裁定」那塊（誠實邊界）

- kernel 是 **back-of-envelope 估算**（DR 自身定位），**非**真跑 vLLM/SGLang benchmark——數字是公式產物非實測。
- 優化技術（PagedAttention/RadixAttention/SQ8/DiskANN）只**援引量化效果當槓桿建議**，不重實作那些引擎。

### ❌ DR 講了但 `capacity_kernel.py` 不驗證

- **架構決策本身**（買不買卡 / 開不開 FP8）= 人的 LAND-DECISION，kernel 只給數字 + 綁定約束 + 槓桿。
- **真實 benchmark 數字**（DR 引用的 throughput/latency 實測）— 範圍外。

---

## fullstack-design-judge ← 分散式前後端/BFF/Agent-async DR

源 DR：[`現代分散式系統架構下前後端需求拆分、BFF 模式演進與 AI Agent 異步任務調度之深度技術研究報告.md`](<現代分散式系統架構下前後端需求拆分、BFF 模式演進與 AI Agent 異步任務調度之深度技術研究報告.md>)
· 落地產物：[`sandboxes/fullstack-design-judge/RUN.md`](../sandboxes/fullstack-design-judge/RUN.md)
· 入口：[`/fullstack-design-judge`](../.claude/commands/fullstack-design-judge.md)（或直接跑 `sandboxes/fullstack-design-judge/src/judge_selftest.py`；composes self-correcting-loop）

### ✅ 跑 `judge_selftest.py` 即真實復現

| DR 章節 | DR 原文敘述 | RUN.md 跑出的證據 |
|---|---|---|
| **前後端需求拆分 / SoC** | 「契約先行 SSOT、前端不持權威計算、關注點分離四步驟」 | macro rubric 10 軸 + micro rubric 11 軸（runnable/rubric kind 切分）；selftest `combined_eq_macro_union_micro` 機械驗無漂移 |
| **BFF 模式演進** | 「BFF 聚合層、BFF vs Gateway 分野、BFF-OAuth 拓撲」 | rubric 對應軸（5/6/7）；DECIDE 復用 self-correcting-loop kernel，`CONSUMED:self-correcting-loop` 印在 trace |
| **Agent 異步任務調度** | 「異步解耦、協議取捨、並行扇出、任務可觀測」 | micro 軸 runnable（idempotency / cookie 四屬性 / 契約測試）+ rubric（串流韌性 / 任務可觀測）；`single_fail_iterating` 證 ITERATING+focus |

### ⚠ 只落地「rubric 標準」那塊（誠實邊界）

- 唯一新增 = **DR 蒸餾的領域 rubric**；DECIDE 迴圈引擎是**復用** self-correcting-loop，非重造。
- kernel 保證 FINAL 機械蘊含於**所宣稱**分數，**不**保證分數本身誠實——評分是 LLM/人 VERIFY 職責。

### ❌ DR 講了但 selftest 不驗證

- **opinionated 絕對主張**（「SSE 最優」「扇出 60-70%」）— rubric 已改成條件式（external-verified RFC/IETF/OWASP），不當絕對對錯判。
- **真 artifact 的代碼/測試** 才能跑 runnable 軸真 exit code；純設計文件用 `.macro.` rubric。

---

## self-correcting-loop — 無 DR

`self-correcting-loop` **不源自 DR**，而是源自使用者直接給的 PLAN/DO/VERIFY/DECIDE 迴圈協定，故不在本對應圖內。
它執行 [`/self-correcting-loop`](../.claude/commands/self-correcting-loop.md) 達成的是**那個協定**（確定性 DECIDE 閘），
真實結果見 [`sandboxes/self-correcting-loop/RUN.md`](../sandboxes/self-correcting-loop/RUN.md)。

---

*邊界誠實聲明：本檔的「DR 原文敘述」是綜述引用、非已查證事實；「❌ / ⚠」欄是吸收時 external-verify 的裁定。
逐條查證的完整核對過程不在本檔——這裡只呈現「落地 vs 宣稱」的邊界結論。*
