---
schema: sandbox-causal-chain/v1
sandbox: turbovec
iso: "2026-06-18"
chain:
  - concept: "純本地 turbovec RAG workload：deterministic seeded 向量建索引 + self-query（recall_at1=1.0），offline，stdlib+numpy+turbovec"
    landed_artifact: "sandboxes/turbovec/src/turbovec_rag.py"
    wiring_ref: "sandboxes/turbovec/src/containment_rag_probe.py"
    wiring_anchor: "turbovec_rag.py"
    runtime_evidence_ref: "sandboxes/turbovec/trace/2026-06-18-containment-rag-verdict.json"
    iso: "2026-06-18"
  - concept: "containment-RAG 對抗驗證 probe（composes openshell-containment 的 sandbox_runner，Slop #2 無新 exec engine）：ns-sandbox 內跑 workload + egress 檢查 → count_metric==0"
    landed_artifact: "sandboxes/turbovec/src/containment_rag_probe.py"
    wiring_ref: "sandboxes/turbovec/tests/test_containment_rag_probe.py"
    wiring_anchor: "containment_rag_probe"
    runtime_evidence_ref: "sandboxes/turbovec/trace/2026-06-18-containment-rag-verdict.json"
    iso: "2026-06-18"
  - concept: "offline wheel 注入：host pip download（abi3 aarch64）→ openshell sandbox upload → in-sandbox pip --no-index（egress default-deny 下不需網路）"
    landed_artifact: "sandboxes/turbovec/src/stage_turbovec_wheels.sh"
    wiring_ref: "sandboxes/turbovec/SKILL.md"
    wiring_anchor: "stage_turbovec_wheels.sh"
    runtime_evidence_ref: "execution/state/turbovec-adlc-scaffold-trace.jsonl"
    iso: "2026-06-18"
  - concept: "接口暴露 /turbovec /command + DCI 注入沙盒內 turbovec 真實狀態；fold_in_sandbox_gate 三層 LIVE"
    landed_artifact: "sandboxes/turbovec/SKILL.md"
    wiring_ref: "sandboxes/PANORAMA.md"
    wiring_anchor: "turbovec"
    runtime_evidence_ref: "sandboxes/turbovec/trace/2026-06-18-fold-in-gate.record.json"
    iso: "2026-06-18"
  - concept: "scaffold runtime 驗證 + land-plan 完成 record：18 PASS / 0 FAIL Session-LIVE + REQUIRED_LAND_PLAN_V2 九步 COMPLETE"
    landed_artifact: "<private — northstar skill layer, not mirrored>"
    wiring_ref: "docs/plans/2026-06-18-turbovec-adlc/03-ledgers-and-gates.md"
    wiring_anchor: "2026-06-18-turbovec-adlc-scaffold-liveness.yaml"
    runtime_evidence_ref: "data/production/flywheel-runs/2026-06-18T18:01:45Z-turbovec-adlc.flywheel-run.yaml"
    iso: "2026-06-18"
---

# causal-chain — turbovec sandbox (技術落地脈絡)

> 沙盒內因果鏈：外部概念 → bridge → build → 對抗驗證 → 接口暴露。機械可驗（`flywheel_run_gate --causal-chain`
> 逐 ref）。與 `absorption-form.md`（flywheel 吸收的形式）**分開**，禁合併。

| 階段 | 內容 | join 點（git/path/trace） |
|------|------|--------------------------|
| 外部概念 | turbovec DR thesis：向量資料庫去中心化為 embedded `pip install`（TurboQuant/ICLR-2026；16× 壓縮 1536-d FP32 6144 B → 384 B；abi3；online ingest）。**外部查證為真**（github 11.8k★，非 DR slop）。 | DR `local_stack/docs/research/…turbovec…RAG 重構分析.md`；primary `github.com/RyanCodrai/turbovec`（stealth_fetch 2026-06-18） |
| bridge | northstar P0 = Zero-API / 100% local Ollama / air-gapped。turbovec 的 load-bearing 價值不是「比 FAISS 快」（primary 證 x86 2-bit 反而慢 ~8%）而是 **完全本地氣隙 RAG**——正中 P0。落地形態 = ADLC 沙盒 instance #3（composition，非新引擎）。 | `docs/plans/2026-06-18-turbovec-adlc/00-intent-and-knowhow.md` §Why-First/§S0 |
| build | turbovec staged 進 ns-sandbox（offline abi3 wheel upload）+ pure-local RAG workload + containment-compose probe。reuse `sandbox_runner`（Slop #2，無新 exec engine）。 | `src/turbovec_rag.py` · `src/containment_rag_probe.py` · `src/stage_turbovec_wheels.sh` |
| 對抗驗證 | `containment_rag_probe` 2 case（rag_works_offline recall_at1=1.0 ∧ rag_egress_denied）→ `count_metric==0` = turbovec 在 default-deny egress 下返回正確鄰居 = **air-gapped RAG 機器證明**（DDR-031，非斷言）。classifiers 5 單測雙向 discrimination green。 | `trace/2026-06-18-containment-rag-verdict.json` · `tests/test_containment_rag_probe.py`（5 passed） |
| 接口暴露 | SKILL.md 創建 `/turbovec` /command + C2 DCI（trace tail + 沙盒內 turbovec 版本真實狀態）+ PANORAMA block + `fold_in_sandbox_gate` 三層 verdict。 | `SKILL.md`（C1-C5）· `manifest.yaml` · `../PANORAMA.md` row |
