---
schema: sandbox-absorption-form/v1
sandbox: turbovec
iso: "2026-06-18"
absorption_chain:
  form: "獨立沙盒落地吸收"
  source_dr: "local_stack/docs/research/嵌入式向量資料庫的技術演進與策略變革：以 turbovec 及 TurboQuant 演算法為核心的 RAG 重構分析.md"
  bridge_ref: "NONE-direct-admit"
  run_records:
    - "data/production/flywheel-runs/2026-06-18T18:01:45Z-turbovec-adlc.flywheel-run.yaml"
  fold_in_targets:
    - "sandboxes/PANORAMA.md"
    - "<private — northstar skill layer, not mirrored>"
  land_plan_ref: "docs/plans/2026-06-18-turbovec-adlc"
---

# absorption-form — turbovec sandbox (flywheel 吸收了什麼形式)

> flywheel 吸收形式因果鏈：pruning verdicts / cut_class / runtime_comparison。**誠實邊界（Slop #18）**：
> 顯式列出什麼**沒**落地。與 `causal-chain.md`（技術落地脈絡）分開。本沙盒是 **--land-plan** 落地（非
> --dr 吸收，按構造無 bridge 步）→ 連回 `docs/plans/2026-06-18-turbovec-adlc/` + flywheel-run record。

| 形式維度 | 本沙盒吸收進 flywheel 的形式 | join 點 |
|---------|---------------------------|---------|
| pruning verdicts | **adopt**：turbovec-as-air-gapped-local-index + **containment-compose 證明**（在 ns-sandbox 內跑，egress 拒 → air-gapped 是機器事實）。**cut**：DR 的 hype——「比 FAISS 快」（primary 證 x86 2-bit 慢 ~8%，只 ARM+x86-4bit 勝）、「接近香農極限」（實為香農下界 2.7×）、「TurboQuant 驅動 llama.cpp/MLX KV-cache，H100 8×」（primary **未支持** = UNVERIFIED，PG-102 不傳播、不落地）。 | `00-intent §Know-How` · turbovec README（stealth_fetch） |
| cut_class | **adopted**（air-gapped index，runtime-proven count_metric==0）· **declined-pool**（real-Ollama-embedded corpus——v1 用 deterministic seeded 向量，保 gate 確定性+offline；Ollama 是 flaky 外部依賴）· **narrowed→SHARPENED**（drop-in-replacement 是**範疇錯誤** index≠database；cc-20260618 runtime-trace 重標為 scoped single-collection backend swap，demand-gated hybrid default-off。見下 §生態系整合評估） | `src/turbovec_rag.py`（seeded）· `CONTEXT.md` declined-pool/narrowed |
| runtime_comparison | **硬數據**（designed test，非辯論——C5/[[pruning-verdict-needs-designed-test-or-explicit-cut-class]]）：① 壓縮 1536-d FP32 6144 B/vec vs turbovec 2-bit 384 B/vec = 16×（README 機制，external-verified）② air-gap：workload 在 egress 拒環境下 `count_metric==0`（`containment_rag_probe` trace `trace/2026-06-18-containment-rag-verdict.json`）vs permissive baseline 下 egress 會 SUCCEED（count>0）= discrimination 真存在，非 placebo。 | `trace/2026-06-18-containment-rag-verdict.json`（runtime tier 產） |

## 生態系整合評估（cc-20260618 runtime-trace fold-in；ultracode workflow wbi995na5）

> 用戶 admit「是否整合 turbovec / 如何遷移 / 先 runtime trace 驗效能」→ 9-agent workflow 在 northstar **真實**
> `doc_embeddings`（768-d，live ChromaDB :8100）上跑 runtime trace + adversarial 驗證。完整報告 →
> [`INTEGRATION-EVALUATION.md`](../../docs/plans/2026-06-18-turbovec-adlc/INTEGRATION-EVALUATION.md)。

**裁定（硬數據）**：NARROWED **維持並 SHARPENED**——「drop-in-replacement」是**範疇錯誤**：turbovec = vector
**INDEX**（dense kNN + id-allowlist），northstar 消費面 = vector **DATABASE**（`server.py` metadata
where-filter `project $in` / 多 collection RRF / 多進程 WAL）。dense-recall core ≈ 消費面 5%，wholesale swap =
在 index 上重造 database 的 95%。重新標：`drop-in（未來）` → **`scoped single-collection backend swap（demand-gated, hybrid, default-off）`**。

**runtime_comparison 補（real embeddings，修正之前假設）**：recall@10=**0.957@4-bit**（tail 差：min 0.80 /
p10 0.90；2-bit 崩到 0.892/min 0.60 → 16× 那條不可用），記憶體 **7.9×@4-bit**（≠ README 16×，那是 2-bit）。
三 collection live-verified unit-normalized → **dot==L2==cosine 今日成立**（turbovec dot-only 公平），但**資料屬性
非保證**，需 normalization-drift guard。latency 非 apples-to-apples（in-proc vs HTTP+payload）。

**結論**：**不換 ChromaDB**；hybrid 單 collection backend 是唯一 data-supported 路徑，但 **demand 未到不啟用**
（Slop #100 / human-admit）。真正整合工作屬 `sandboxes/_integration/` zone，demand-pull 才動。沙盒 adopted
（air-gapped index，count_metric==0）已完整、不變。port 修正：ChromaDB 是 :8100 非 :8000（:8000 是 dynamodb）。
