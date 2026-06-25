# DR 公式溯源 — AI Agent 容量估算框架（49 圖轉錄 + 5 步檢核表）

> **Source DR**: `the source project/docs/research/AI Agent 時代的計算系統容量估算與架構設計研究報告.md`
> （Gemini DR；49 張公式/數值/變數全部渲染成 reference-style base64-PNG，純文字 grep 會漏掉全部數學）。
> **吸收方法**: 解碼 49 圖 → 4-agent 讀圖轉錄 Workflow + 1 完整性 critic（親自 Read 核對 §5 檢核表 8 圖 +
> 核心公式 5 圖）→ critic verdict **PASS（高保真，零亂碼）**。本檔 = `capacity_kernel.py` 的公式真值來源。

## 核心命門（core thesis）

範式從「一請求一調用」轉為「一請求觸發 N_loops 思考循環」的**代理邏輯放大效應**。容量瓶頸全面移轉到
GPU 顯存(VRAM) / Token 吞吐 / 推理延遲 / KV-Cache 管理。**決定最大併發的不是 CPU/網路，而是 GPU 的
KV-Cache 顯存容積**。一條五步公式鏈把同一組瓶頸數字**同時**翻成宏觀 sizing 與微觀代碼優化。

## 五步架構檢核表（§5 — rubric 本體；formula / 宏觀架構影響 / 微觀代碼槓桿）

| Step | 核心提問 | 公式 | 宏觀架構影響 | 微觀代碼槓桿 |
|------|----------|------|--------------|--------------|
| **1 Agent 放大率** | 一次任務 Agent 平均呼叫幾次 LLM？ | `Agent QPS = User QPS × N_loops`（image42；範例 10×4=40） | 後端併發佇列深度 + 平台 RPM 限額 | 最長思考步數強行中斷；動態上下文裁剪 + 摘要壓縮 |
| **2 Token 吞吐量** | 每秒最大消耗多少 Input/Output Token？ | `Input TPS = Agent QPS × S_prompt`；`Output TPS = Agent QPS × S_completion`（image43/44；範例 40×3000=120k / 40×500=20k）。Prefill 計算密集 vs Decode 頻寬受限，分開計 | 雲端 TPM 預算 / 地端集群吞吐（顯卡張數/頻寬選型） | 前綴脈絡快取避免重覆計算 |
| **3 顯存與併發** | context 長 × 併發數，顯存頂得住？ | `W_static = Params × 2`（image45,FP16）；`KV = (2·L·H_kv·D_head·S·B·Prec)/TP`（image46，**比 §3 per-token 公式多 S/B/TP 三維度**）。範例 70B→140GB + Batch32@4K KV 40GB ≈ 180GB > 單張 80GB | 採購幾張卡 + 張量並行(TP)/流水線並行規模。瓶頸 = KV-Cache 顯存容積 | vLLM PagedAttention 分頁（浪費<4%、併發×2-4）；FP8 KV 量化（顯存減半） |
| **4 前綴快取調度** | 公共前綴重覆率多高？ | 動態快取命中率 **> 30% 損益平衡點**（image47） | TTFT + 運算 TCO；高命中降硬體規格 | SGLang RadixAttention 基數樹（-80% 重複 Prefill、近零開銷分支複製）；規範化 Prompt 格式 |
| **5 記憶與知識庫** | RAG 向量維度 × Chunk 數多大？ | `RAM = N_chunks · d_dim · 4 · α_index`（image48，FP32 每維 4 bytes，HNSW α≈1.5~1.8）。範例 1000萬×3072×4×1.5≈184.32GB ⇒ 建議 256GB | Vector DB 主機 RAM + SSD 隨機讀 IOPS（HNSW 須全量常駐 RAM） | SQ8 向量壓縮（~1.8x→~0.3x）；超大規模切 DiskANN（~0.08x，NVMe SSD） |

## 四大核心指標公式（§2，含變數定義）

- **指標一 Agent QPS**：`Agent QPS = User QPS × N_loops`（N_loops = Agent 放大係數 = 單請求平均 LLM 呼叫數）。
- **指標二 Token 吞吐**：`Input TPS = Agent QPS × 平均輸入 tokens`；`Output TPS = Agent QPS × 平均輸出 tokens`。
- **指標三 顯存**：
  - 靜態權重 `Static VRAM (Bytes) = 參數量 × Precision Bytes`（FP16/BF16=2, FP8=1, FP4=0.5）。
  - KV per token `= 2 × L × H_kv × D_head × Precision Bytes`（2=K&V 雙張量；L=層數；H_kv=KV 注意力頭數;
    D_head=每頭維度）。Llama3-70B: 2×80×8×128×2 = **327,680 Bytes ≈ 0.31 MiB/token**。
  - §5 完整式（加併發+並行）：`KV = (2·L·H_kv·D_head·S·B·Prec)/TP`（S=context 長, B=batch, TP=張量並行）。
- **指標四 RAG RAM**：`RAM = N_chunks × d_dim × Precision Bytes(float32=4) × α_index`（HNSW α 1.5~1.8）。

## §3/§4 優化前沿（kernel 的 LEVERS 知識庫來源）

- **PagedAttention (vLLM)**：OS 式分頁，非連續物理塊按需分配；內存浪費<4%、單卡併發↑2-4x。局限：主要針對單請求內碎片，跨請求/跨會話複用弱。
- **RadixAttention (SGLang)**：基數樹維護所有已處理 token 序列，自動共享最長公共前綴 KV 物理頁；agent swarm / MCTS 分支下近零開銷分支複製，-80% 重複 Prefill，壓低 TTFT。
- **Chunked Prefill**：長 prompt 切固定 chunk（如 512 token）與 decode 打包進同一前向，抹平 ITL 卡頓。
- **Speculative Decoding**：草擬模型（目標 1/10~1/50）連猜 K 個候選 token，目標模型單次並行驗證；2-3.6x 加速。**邊界：batch>32 時 GPU 已飽和，草擬轉純開銷反降吞吐**。
- **向量存儲權衡表**：HNSW float32(~1.8x, 1-5ms, 98-99%) / SQ8(~0.3x, 5-10ms, 93-97%, 推薦生產) / PQ(~0.12x, 10-20ms, 70-80%) / DiskANN(~0.08x, 15-30ms, 95-98%, 億級+NVMe)。

## DR 自身缺陷（mirror-finding，the issue）

DR **混用 GB(十進位 ÷1e9) 與 GiB(二進位 ÷2^30)**：權重「70×2=140 GB」與 RAG「122.88 GB」是十進位；
KV-Cache「0.31 MB / 1.25 GB / 40 GB」是二進位；總計「180 GB」= 140(十進位)+40(二進位) 的混用近似。
`capacity_kernel` 以 **bytes 為真值**，同時報 GiB+GB 雙單位，避免 budget 比較被靜默 ~7% 誤差咬到；
selftest 在各自原始單位下逐項複現 DR 數字以證忠實，同時揭露此不一致。

## critic 列出的 4 處非阻斷補強（已併入 kernel）

1. image46 引入 S/B/TP 三維度（§5 KV 公式 vs §3 per-token 公式的核心增量）→ kernel `estimate()` 全部納入。
2. image22 雙重角色（KV Precision Bytes 與 RAG float32=4B）→ kernel 分別以 `model.precision_bytes` 與 `rag.precision_bytes` 表達。
3. image49 截斷的 α≈ → 值補自 image33(1.5)/image34(1.8)/image38(1.5 範例採用) → kernel `DEFAULT_HNSW_ALPHA=1.5`。
4. 投機解碼 batch>32 退化邊界 + 2-3.6x/1-10~1-50 數字 → kernel `SPEC_DECODE_BATCH_CEILING=32` + `LEVERS["latency"]`。
