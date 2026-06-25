#!/usr/bin/env python3
"""capacity_kernel — deterministic capacity ESTIMATOR + feasibility RUBRIC JUDGE for AI-Agent
serving systems, encoding the complete framework of the DR
"AI Agent 時代的計算系統容量估算與架構設計研究報告".

WHY (the demand,  human-admitted): a back-of-the-envelope capacity estimate for an
agentic system is only useful if it is (a) faithful to the real formulas, (b) deterministic (no
LLM-judge — deterministic (no LLM-judge)), and (c) actionable at BOTH scales the DR insists on: a single set of
bottleneck numbers must drive the MACRO architecture decision (how many GPUs / tensor-parallel
size / vector-DB RAM) AND the MICRO code lever (PagedAttention / FP8 KV / RadixAttention / SQ8 /
DiskANN). This kernel MECHANIZES the DR's 5-step checklist (§5) into a determinate function: it
computes the five metrics from explicit inputs and JUDGES feasibility against explicit budgets,
returning FEASIBLE iff every constrained criterion is within budget, else INFEASIBLE + the binding
constraint + the DR-prescribed macro & micro lever. "FEASIBLE" is entailed by actual numbers vs
budgets, never by an agent's prose claim.

COMPOSES the existing loop layer (no new engine — no new engine): `judge` exits 0 (FEASIBLE) /
3 (INFEASIBLE), the SAME exit semantics as self-correcting-loop's DECIDE, so this judge can be a
`kind: runnable` criterion inside a /self-correcting-loop rubric — i.e. an LLM iterating an agent
system architecture gets a deterministic "capacity-feasible" gate that points the next iteration at
the binding constraint + its DR lever.

DETERMINISM: pure functions; no datetime.now()/random — the only timestamp source is an explicit
`iso` argument (parity with loop_kernel / the sandbox gate). All sizes are computed EXACTLY in
bytes; GiB (÷2**30) and GB (÷1e9) are presentation conversions.

UNIT NOTE (a DR mirror-finding, the issue): the source mixes binary and decimal "GB" — model weights
(70×2=140 "GB") and RAG (122.88 "GB") are decimal (÷1e9) while the KV-cache example (0.31 "MB",
1.25 "GB", 40 "GB") is binary (÷2**30). This kernel keeps the EXACT byte count as truth and reports
BOTH gib and gb so a budget comparison is never silently off by ~7%; the selftest reproduces every
DR figure in its own stated unit to prove faithfulness while surfacing the inconsistency.

EXIT SEMANTICS (CLI):
  selftest : 0 = kernel reproduces the DR worked example + judge discriminates · 1 = a check failed
  estimate : 0 = printed the five-metric estimate · 1 = bad input
  judge    : 0 = FEASIBLE · 3 = INFEASIBLE (distinct non-error code so a loop driver can branch) · 1 = bad input
  state    : 0 = printed a bounded loop-state snapshot · 1 = no such loop / unreadable

Related docs:
- Interface contract: sandboxes/capacity-estimation/SKILL.md (C1-C5) + manifest.yaml
- Source formula inventory (provenance): sandboxes/capacity-estimation/docs/dr-formula-inventory.md
- Loop governance + DCI 5-rule contract: .claude/skills/adlc/skill.md S1/S3
- Convention: sandboxes/README.md + sandboxes/_TEMPLATE/ + sandboxes/self-correcting-loop/ (sibling kernel)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

GIB = 1 << 30          # 2**30 — binary gibibyte
GB = 1_000_000_000     # 1e9   — decimal gigabyte (how GPU/RAM hardware is marketed)
DEFAULT_CARD_VRAM_GB = 80          # NVIDIA A100/H100 80GB (DR baseline card)
DEFAULT_RAG_PRECISION = 4          # float32 vectors (DR default; SQ8 would be 1)
DEFAULT_HNSW_ALPHA = 1.5           # HNSW index overhead multiplier (DR range 1.5–1.8)
DEFAULT_PREFIX_BREAKEVEN = 0.30    # DR §5 Step-4: dynamic cache hit-rate breakeven point (image47)
SPEC_DECODE_BATCH_CEILING = 32     # DR §4 boundary: speculative decoding degrades when batch > 32

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SpecError(Exception):
    """Fail-loud input defect (malformed spec / budgets). Never silently coerced."""


# ── the DR optimization knowledge base (§3/§4 + §5 column-5) ───────────────────
# Maps each binding constraint to the DR-prescribed MACRO architecture move + MICRO code lever,
# with the source's quantified effect and applicability boundary. This is the "guides macro+micro"
# half of the deliverable: an INFEASIBLE verdict returns the relevant entry verbatim.
LEVERS = {
    "amplification": {
        "macro": "限制後端推理服務器併發佇列深度 / 申請更高平台 RPM；用 N_loops 反推所需後端吞吐。",
        "micro": "設置最長思考步數強行中斷（capped reasoning loops）；動態上下文裁剪 + 摘要壓縮以壓低 N_loops 與單輪 prompt 膨脹。",
    },
    "token_throughput": {
        "macro": "依 input/output TPS 估雲端 TPM 預算或地端集群吞吐；逼近企業 TPM 上限須向供應商提額。",
        "micro": "引入前綴脈絡快取（Context Caching）避免重覆計算共享前綴；input(Prefill,compute-bound)/output(Decode,bw-bound)分離計費與調度。",
    },
    "vram_concurrency": {
        "macro": "增購顯卡或提高張量並行度 TP（KV 顯存 ÷TP 分攤）；瓶頸是 KV-Cache 顯存容積而非 CPU/網路。",
        "micro": "啟用 vLLM PagedAttention 記憶體分頁（內存浪費<4%、單卡併發↑2-4x）；啟用 FP8 KV-Cache 量化（動態顯存直接減半）。",
        "effects": {"paged_attention": "fragmentation<4%, concurrency x2-4 (intra-request only; weak cross-request reuse)",
                    "fp8_kv": "halves KV-cache VRAM",
                    "tensor_parallel": "divides KV-cache by TP (DR image46 puts /TP on the KV term only; weights stay un-sharded in the DR model — real TP shards weights too, not modeled)"},
    },
    "prefix_cache": {
        "macro": "對多智能體/RAG 鏈條的公共前綴，要求 TTL 內動態命中率 > 損益平衡點，否則 TTFT/TCO 惡化。",
        "micro": "部署 SGLang RadixAttention 基數樹（最長公共前綴自動共享 KV，-80% 重複 Prefill、近零開銷分支複製）；規範化 Prompt 格式最大化命中。",
    },
    "rag_ram": {
        "macro": "向量 DB 主機 RAM 須容下全量 HNSW 索引常駐（毫秒級檢索）；超量則加 RAM 或切壓縮/磁碟索引。",
        "micro": "SQ8 向量壓縮（內存 ~1.8x→~0.3x，召回 93-97%）；超大規模切 DiskANN 磁碟導航圖（~0.08x，跑 NVMe SSD）。",
    },
    "latency": {
        "macro": "高併發混合調度下平衡 TTFT 與 decode 吞吐；注意投機解碼在高批次下退化。",
        "micro": ("分塊預填充 Chunked Prefill（512-token chunk 與 decode 打包，抹平 ITL）；"
                  f"投機性解碼 Speculative Decoding（草擬模型 1/10-1/50，2-3.6x 加速）——"
                  f"但 batch>{SPEC_DECODE_BATCH_CEILING} 時 GPU 已飽和，草擬轉純開銷反降吞吐。"),
    },
}

# DR §2 vector-storage tradeoff table (L113-118): memory multiplier vs P95 latency vs recall.
# recall_low / p95_high = conservative bounds (recall lower-bound, latency upper-bound) so the
# index recommender (recommend_index) can pick the cheapest row that PROVABLY meets a budget.
VECTOR_INDEX_TABLE = [
    {"index": "HNSW float32", "mem_mult": 1.8, "p95_ms": "1-5", "recall": "98-99%",
     "recall_low": 0.98, "p95_high": 5, "use": "延遲極度敏感、預算充足的即時系統"},
    {"index": "HNSW + SQ8 (uint8)", "mem_mult": 0.3, "p95_ms": "5-10", "recall": "93-97%",
     "recall_low": 0.93, "p95_high": 10, "use": "推薦的生產環境配置（成本/精度平衡）"},
    {"index": "HNSW + PQ", "mem_mult": 0.12, "p95_ms": "10-20", "recall": "70-80%",
     "recall_low": 0.70, "p95_high": 20, "use": "超大型粗篩 / 記憶體極度受限的邊緣設備"},
    {"index": "DiskANN", "mem_mult": 0.08, "p95_ms": "15-30", "recall": "95-98%",
     "recall_low": 0.95, "p95_high": 30, "use": "億級以上知識庫，配高速 NVMe SSD"},
]


def recommend_index(raw_bytes: float, recall_floor=None, p95_ms_budget=None) -> dict:
    """Active consumption of VECTOR_INDEX_TABLE (DR §2): pick the cheapest-memory index whose
    conservative recall_low >= recall_floor AND p95_high <= p95_ms_budget, computing the resulting
    RAM (raw_bytes × mem_mult). No budget given → the DR default (HNSW float32). None meets the
    budget → {'index': None, ...} so the judge can SURFACE 'no index satisfies recall+latency'.
    This is the 'guide micro code' half: a recall/latency target maps to a concrete index choice."""
    cands = list(VECTOR_INDEX_TABLE)
    if recall_floor is not None:
        cands = [r for r in cands if r["recall_low"] >= recall_floor]
    if p95_ms_budget is not None:
        cands = [r for r in cands if r["p95_high"] <= p95_ms_budget]
    if not cands:
        return {"index": None, "reason": "no index meets recall_floor+p95_ms_budget", "ram": None}
    if recall_floor is None and p95_ms_budget is None:
        pick = VECTOR_INDEX_TABLE[0]                 # DR default = HNSW float32
    else:
        pick = min(cands, key=lambda r: r["mem_mult"])   # cheapest memory among those meeting the budget
    return {"index": pick["index"], "mem_mult": pick["mem_mult"], "recall": pick["recall"],
            "p95_ms": pick["p95_ms"], "ram": _both_units(raw_bytes * pick["mem_mult"]), "use": pick["use"]}


# ── spec parsing / validation (fail-loud) ──────────────────────────────────────

def _num(d: dict, key: str, where: str, *, required=True, default=None, positive=True):
    if key not in d:
        if required:
            raise SpecError(f"{where}: missing required numeric field '{key}'")
        return default
    v = d[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SpecError(f"{where}.{key} must be a number, got {v!r}")
    if positive and v <= 0:
        raise SpecError(f"{where}.{key} must be > 0, got {v!r}")
    return v


@dataclass(frozen=True)
class Spec:
    label: str
    user_qps: float
    n_loops: float
    avg_input_tokens: float
    avg_output_tokens: float
    params_billions: float
    precision_bytes: float
    layers: int
    kv_heads: int
    head_dim: int
    context_length: int
    batch_size: int
    tensor_parallel: int
    card_vram_gb: float
    rag_chunks: float
    rag_dim: int
    rag_precision_bytes: float
    hnsw_alpha: float
    rag_recall_floor: float | None      # optional recall target → drives index recommendation (micro lever)
    rag_p95_ms_budget: float | None     # optional P95 latency budget → drives index recommendation
    prefix_hit_rate: float | None
    prefix_breakeven: float


def load_spec(obj: dict) -> Spec:
    if not isinstance(obj, dict):
        raise SpecError("spec must be a JSON object")
    w = obj.get("workload", {}) or {}
    m = obj.get("model", {}) or {}
    s = obj.get("serving", {}) or {}
    r = obj.get("rag", {}) or {}
    p = obj.get("prefix_cache", {}) or {}
    breakeven = _num(p, "breakeven", "prefix_cache", required=False, default=DEFAULT_PREFIX_BREAKEVEN)
    if not (0 < breakeven < 1):
        raise SpecError(f"prefix_cache.breakeven must be a fraction in (0,1), got {breakeven!r}")
    hit = p.get("hit_rate")
    if hit is not None and (isinstance(hit, bool) or not isinstance(hit, (int, float)) or not (0 <= hit <= 1)):
        raise SpecError(f"prefix_cache.hit_rate must be a fraction in [0,1] or omitted, got {hit!r}")
    return Spec(
        label=str(obj.get("label", "unnamed")),
        user_qps=_num(w, "user_qps", "workload"),
        n_loops=_num(w, "n_loops", "workload"),
        avg_input_tokens=_num(w, "avg_input_tokens", "workload"),
        avg_output_tokens=_num(w, "avg_output_tokens", "workload"),
        params_billions=_num(m, "params_billions", "model"),
        precision_bytes=_num(m, "precision_bytes", "model"),
        layers=int(_num(m, "layers", "model")),
        kv_heads=int(_num(m, "kv_heads", "model")),
        head_dim=int(_num(m, "head_dim", "model")),
        context_length=int(_num(s, "context_length", "serving")),
        batch_size=int(_num(s, "batch_size", "serving")),
        tensor_parallel=int(_num(s, "tensor_parallel", "serving", required=False, default=1)),
        card_vram_gb=_num(s, "card_vram_gb", "serving", required=False, default=DEFAULT_CARD_VRAM_GB),
        rag_chunks=_num(r, "chunks", "rag"),
        rag_dim=int(_num(r, "dim", "rag")),
        rag_precision_bytes=_num(r, "precision_bytes", "rag", required=False, default=DEFAULT_RAG_PRECISION),
        hnsw_alpha=_num(r, "hnsw_alpha", "rag", required=False, default=DEFAULT_HNSW_ALPHA),
        rag_recall_floor=_recall_floor(r),
        rag_p95_ms_budget=_num(r, "p95_ms_budget", "rag", required=False, default=None),
        prefix_hit_rate=hit,
        prefix_breakeven=breakeven,
    )


def _recall_floor(r: dict):
    rf = r.get("recall_floor")
    if rf is None:
        return None
    if isinstance(rf, bool) or not isinstance(rf, (int, float)) or not (0 < rf <= 1):
        raise SpecError(f"rag.recall_floor must be a fraction in (0,1] or omitted, got {rf!r}")
    return rf


def _both_units(nbytes: float) -> dict:
    """Exact bytes + both conversions, so a budget comparison is never silently GB/GiB-confused."""
    return {"bytes": nbytes, "gib": round(nbytes / GIB, 4), "gb": round(nbytes / GB, 4)}


# ── the five-metric estimator (DR §2 + §5 formulas, exact in bytes) ─────────────

def estimate(spec: Spec) -> dict:
    """Compute the DR's five core metrics. Pure function of the spec."""
    # Step 1 — Agent amplification (image4/42): Agent QPS = User QPS × N_loops
    agent_qps = spec.user_qps * spec.n_loops
    # Step 2 — Token throughput (image7/8/43/44): TPS = Agent QPS × per-call tokens
    input_tps = agent_qps * spec.avg_input_tokens
    output_tps = agent_qps * spec.avg_output_tokens
    # Step 3a — static model weights (image13/45): bytes = params × precision_bytes
    weights_bytes = spec.params_billions * 1e9 * spec.precision_bytes
    # Step 3b — KV cache. per-token (image17/23): 2 × L × H_kv × D_head × precision
    kv_per_token_bytes = 2 * spec.layers * spec.kv_heads * spec.head_dim * spec.precision_bytes
    # full KV (image46, the §5 form — adds S=context, B=batch, ÷TP tensor-parallel):
    kv_total_bytes = kv_per_token_bytes * spec.context_length * spec.batch_size / spec.tensor_parallel
    total_vram_bytes = weights_bytes + kv_total_bytes
    card_vram_bytes = spec.card_vram_gb * GB
    cards_needed = math.ceil(total_vram_bytes / card_vram_bytes) if card_vram_bytes > 0 else None
    # Step 5 — RAG vector DB RAM (image29/37/39/48): N × d × precision × α_index
    rag_raw_bytes = spec.rag_chunks * spec.rag_dim * spec.rag_precision_bytes
    rag_ram_bytes = rag_raw_bytes * spec.hnsw_alpha
    return {
        "label": spec.label,
        "step1_amplification": {"agent_qps": agent_qps, "rpm_equiv": agent_qps * 60},
        "step2_throughput": {"input_tps": input_tps, "output_tps": output_tps,
                             "total_tps": input_tps + output_tps, "tpm_equiv": (input_tps + output_tps) * 60},
        "step3_vram": {
            "weights": _both_units(weights_bytes),
            "kv_per_token_bytes": kv_per_token_bytes,
            "kv_total": _both_units(kv_total_bytes),
            "total_vram": _both_units(total_vram_bytes),
            "card_vram_gb": spec.card_vram_gb,
            "cards_needed": cards_needed,
        },
        "step4_prefix_cache": {"hit_rate": spec.prefix_hit_rate, "breakeven": spec.prefix_breakeven},
        "step5_rag": {"raw": _both_units(rag_raw_bytes), "with_index": _both_units(rag_ram_bytes),
                      "hnsw_alpha": spec.hnsw_alpha,
                      # ACTIVE consumption of the DR §2 tradeoff table: a recall/latency target → a
                      # concrete index pick + its resulting RAM (the 'guide micro code' deliverable).
                      "recommended_index": recommend_index(rag_raw_bytes, spec.rag_recall_floor,
                                                           spec.rag_p95_ms_budget)},
    }


# ── the deterministic feasibility JUDGE (rubric) ───────────────────────────────

def _criterion(name, computed, budget, ok, *, unit, lever_key):
    return {"name": name, "computed": computed, "budget": budget, "unit": unit,
            "status": "PASS" if ok else "BINDING",
            "lever": LEVERS.get(lever_key) if not ok else None}


def judge(spec: Spec, budgets: dict, est: dict | None = None) -> dict:
    """FEASIBLE iff every CONSTRAINED criterion is within its budget; else INFEASIBLE + binding
    constraints (each carrying the DR macro+micro lever). A criterion with no budget is reported
    as 'not_constrained' (informational, never fails) — so a partial budget never fakes a verdict."""
    if not isinstance(budgets, dict):
        raise SpecError("budgets must be a JSON object (may be empty {})")
    est = est or estimate(spec)
    crits: list[dict] = []
    not_constrained: list[str] = []

    def constrained(key):
        return budgets.get(key) is not None

    # 1 — Agent amplification vs backend RPM
    if constrained("backend_rpm_limit"):
        v = est["step1_amplification"]["rpm_equiv"]; b = budgets["backend_rpm_limit"]
        crits.append(_criterion("amplification_rpm", v, b, v <= b, unit="req/min", lever_key="amplification"))
    else:
        not_constrained.append("amplification_rpm")
    # 2 — Token throughput vs TPM budget
    if constrained("tpm_budget"):
        v = est["step2_throughput"]["tpm_equiv"]; b = budgets["tpm_budget"]
        crits.append(_criterion("token_throughput_tpm", v, b, v <= b, unit="tokens/min", lever_key="token_throughput"))
    else:
        not_constrained.append("token_throughput_tpm")
    # 3 — VRAM / concurrency vs cards available
    if constrained("cards_available"):
        v = est["step3_vram"]["cards_needed"]; b = budgets["cards_available"]
        crits.append(_criterion("vram_concurrency", v, b, v is not None and v <= b,
                                unit="GPU cards", lever_key="vram_concurrency"))
    else:
        not_constrained.append("vram_concurrency")
    # 4 — Prefix-cache hit rate vs breakeven (constrained iff an expected/measured hit_rate is given)
    if spec.prefix_hit_rate is not None:
        v = spec.prefix_hit_rate; b = spec.prefix_breakeven
        crits.append(_criterion("prefix_cache_breakeven", v, b, v >= b, unit="hit-rate", lever_key="prefix_cache"))
    else:
        not_constrained.append("prefix_cache_breakeven")
    # 5 — RAG RAM vs host RAM (compare in GB-decimal, the unit hosts are marketed in)
    if constrained("host_ram_gb"):
        v = est["step5_rag"]["with_index"]["gb"]; b = budgets["host_ram_gb"]
        crits.append(_criterion("rag_ram", v, b, v <= b, unit="GB", lever_key="rag_ram"))
    else:
        not_constrained.append("rag_ram")
    # 6 — speculative-decoding boundary (DR §4): if the architecture PLANS spec-decode
    # (budgets.spec_decode_enabled), it BINDS once batch_size > SPEC_DECODE_BATCH_CEILING, where the
    # DR says spec-decode degrades to pure overhead and can LOWER total throughput. Enforces the
    # documented boundary instead of leaving it as inert prose.
    if budgets.get("spec_decode_enabled") is True:
        v = spec.batch_size; b = SPEC_DECODE_BATCH_CEILING
        crits.append(_criterion("spec_decode_batch_ceiling", v, b, v <= b,
                                unit="batch", lever_key="latency"))
    else:
        not_constrained.append("spec_decode_batch_ceiling")

    binding = [c["name"] for c in crits if c["status"] == "BINDING"]
    verdict = "FEASIBLE" if not binding else "INFEASIBLE"
    return {"verdict": verdict, "label": spec.label, "binding": binding,
            "criteria": crits, "not_constrained": not_constrained,
            "evaluated": len(crits), "estimate": est}


# ── bounded loop-state tracking (when a judge feeds an iteration loop) ──────────

def advance(state: dict, iso: str, verdict: dict) -> dict:
    state.setdefault("iterations", [])
    state["iterations"].append({
        "iteration": len(state["iterations"]) + 1, "iso": iso, "label": verdict["label"],
        "verdict": verdict["verdict"], "binding": verdict["binding"],
    })
    state["verdict"] = verdict["verdict"]
    return state


# ── loop-engineering composition: project the judge to a /self-correcting-loop scorecard ───────
# The DR Step-1..5 budgeted criteria ARE the fleet's loop_kernel-compatible Judge dims. scorecard projects
# each CONSTRAINED criterion to a `runnable` exit code (0=within budget / 1=BINDING) so an existing
# /self-correcting-loop rubric can DECIDE multi-criterion over capacity — the DECIDE stays loop_kernel's, this
# kernel only measures (estimate) + projects (no new engine). Mirrors arch-fitness
# scorecard_from_report; recipes/ ships the rubric + the PLAN/DO/VERIFY/DECIDE composition.
CRITERION_IDS = ("amplification_rpm", "token_throughput_tpm", "vram_concurrency",
                 "prefix_cache_breakeven", "rag_ram", "spec_decode_batch_ceiling")


def scorecard_from_judge(verdict: dict, dims: list | None = None) -> dict:
    """Project a judge() verdict to a self-correcting-loop 'runnable' scorecard ({criterion_id: exit_code},
    0=within budget / 1=BINDING). Only CONSTRAINED criteria are projectable (an un-budgeted criterion has no
    pass/fail). `dims` restricts to a subset so the scorecard keys == the loop rubric ids EXACTLY (loop_kernel's
    hard contract). Fail-loud on a dim that is unknown or not constrained this run."""
    by_name = {c["name"]: c for c in verdict.get("criteria", [])}   # constrained criteria only
    selected = list(by_name) if dims is None else [d.strip() for d in dims]
    bad = [d for d in selected if d not in by_name]
    if bad:
        raise SpecError(f"unknown/unconstrained scorecard dim(s) {bad}; constrained this run: {sorted(by_name)} "
                        "(give the criterion a budget in --budgets, or drop it from --dims / the loop rubric)")
    return {d: (0 if by_name[d]["status"] == "PASS" else 1) for d in selected}


def _render_state_snapshot(state: dict) -> str:
    """Bounded (<=~10 lines) snapshot for DCI injection (adlc DCI rule 2: bounded output)."""
    iters = state.get("iterations", [])
    lines = [f"capacity loop iterations: {len(iters)}"]
    if iters:
        last = iters[-1]
        lines.append(f"last verdict: {last['verdict']}  (label: {last['label']})")
        lines.append(f"binding constraints: {', '.join(last['binding']) or '— (all within budget)'}")
        if last["binding"]:
            lines.append("→ next iteration: relieve the binding constraint via its DR lever (see judge output).")
    return "\n".join(lines)


# ── IO helpers ─────────────────────────────────────────────────────────────────

def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise SpecError(f"file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise SpecError(f"invalid JSON in {path}: {e}") from e


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _default_state_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "state"


# ── selftest: reproduce the DR worked example + prove the judge discriminates ──

def _approx(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(b))


def _cmd_selftest(iso: str) -> int:
    _dr = _load_json(_FIXTURES / "dr-example-spec.json")
    spec = load_spec(_dr)
    est = estimate(spec)
    checks: list[tuple[str, bool]] = []

    # Faithful reproduction of every DR figure, each in ITS OWN stated unit (the unit-mix the DR uses).
    checks.append(("agent_qps_40", est["step1_amplification"]["agent_qps"] == 40))
    checks.append(("input_tps_120k", est["step2_throughput"]["input_tps"] == 120_000))
    checks.append(("output_tps_20k", est["step2_throughput"]["output_tps"] == 20_000))
    checks.append(("weights_140gb_decimal", _approx(est["step3_vram"]["weights"]["gb"], 140.0)))
    checks.append(("kv_per_token_327680_bytes_exact", est["step3_vram"]["kv_per_token_bytes"] == 327_680))
    checks.append(("kv_total_40gib_binary", _approx(est["step3_vram"]["kv_total"]["gib"], 40.0)))
    checks.append(("rag_raw_122_88gb_decimal", _approx(est["step5_rag"]["raw"]["gb"], 122.88)))
    checks.append(("rag_index_184_32gb_decimal", _approx(est["step5_rag"]["with_index"]["gb"], 184.32)))

    # Judge FEASIBLE path: budgets generous enough that the DR example fits.
    feasible = judge(spec, {"cards_available": 3, "backend_rpm_limit": 3000,
                            "tpm_budget": 9_000_000, "host_ram_gb": 256}, est)
    checks.append(("judge_feasible_when_budgets_met", feasible["verdict"] == "FEASIBLE"))

    # DISCRIMINATION (the self-check a hollow kernel fails): squeeze VRAM cards to 2 → the DR example's
    # 180GB needs 3×80GB cards → vram_concurrency MUST become the binding constraint and flip INFEASIBLE.
    tight = judge(spec, {"cards_available": 2}, est)
    checks.append(("judge_infeasible_when_vram_tight", tight["verdict"] == "INFEASIBLE"))
    checks.append(("binding_is_vram", tight["binding"] == ["vram_concurrency"]))
    checks.append(("binding_carries_micro_lever",
                   any(c["name"] == "vram_concurrency" and c["lever"] and "PagedAttention" in c["lever"]["micro"]
                       for c in tight["criteria"])))

    # prefix-cache discrimination: a hit-rate below breakeven must bind.
    spec_lowhit = load_spec({**_dr, "prefix_cache": {"hit_rate": 0.1, "breakeven": 0.30}})
    lowhit = judge(spec_lowhit, {})
    checks.append(("prefix_cache_below_breakeven_binds",
                   lowhit["verdict"] == "INFEASIBLE" and lowhit["binding"] == ["prefix_cache_breakeven"]))

    # ENHANCEMENT — active vector-index recommendation (DR §2 table consumed, not inert):
    checks.append(("index_default_hnsw", est["step5_rag"]["recommended_index"]["index"] == "HNSW float32"))
    rec = estimate(load_spec({**_dr, "rag": {**_dr["rag"], "recall_floor": 0.93, "p95_ms_budget": 10}}))
    # recall>=0.93 ∧ p95<=10ms: DiskANN(p95<=30) excluded by latency, PQ(recall 0.70) by recall → cheapest = SQ8
    checks.append(("index_recall_latency_picks_sq8",
                   rec["step5_rag"]["recommended_index"]["index"] == "HNSW + SQ8 (uint8)"))

    # ENHANCEMENT — spec-decode batch-ceiling boundary ENFORCED (DR §4 not inert):
    sd_bind = judge(load_spec({**_dr, "serving": {**_dr["serving"], "batch_size": 64}}), {"spec_decode_enabled": True})
    checks.append(("spec_decode_binds_above_ceiling",
                   sd_bind["verdict"] == "INFEASIBLE" and "spec_decode_batch_ceiling" in sd_bind["binding"]))
    checks.append(("spec_decode_ok_at_ceiling",
                   judge(spec, {"spec_decode_enabled": True})["verdict"] == "FEASIBLE"))   # batch 32 == ceiling

    # FLEET loop-composition — the budgeted criteria project to a loop_kernel-compatible runnable scorecard:
    full_budgets = {"backend_rpm_limit": 3000, "tpm_budget": 9_000_000, "cards_available": 2, "host_ram_gb": 256}
    sc = scorecard_from_judge(judge(load_spec({**_dr, "prefix_cache": {"hit_rate": 0.5, "breakeven": 0.30}}),
                                    full_budgets))
    checks.append(("scorecard_keys_are_the_5_criteria",
                   set(sc) == {"amplification_rpm", "token_throughput_tpm", "vram_concurrency",
                               "prefix_cache_breakeven", "rag_ram"}))
    checks.append(("scorecard_values_are_exit_codes", all(v in (0, 1) for v in sc.values())))
    checks.append(("scorecard_vram_binds_exit1", sc["vram_concurrency"] == 1))   # cards 2<3 → 1 (loop focuses it)
    checks.append(("scorecard_within_budget_exit0",
                   sc["amplification_rpm"] == 0 and sc["rag_ram"] == 0 and sc["prefix_cache_breakeven"] == 0))

    # fail-loud on malformed spec
    try:
        load_spec({"workload": {"user_qps": -1}})
        checks.append(("malformed_failloud", False))
    except SpecError:
        checks.append(("malformed_failloud", True))

    ok = all(p for _, p in checks)
    trace = {"schema": "capacity-kernel-selftest/v1", "iso": iso, "ok": ok,
             "checks": [{"name": n, "pass": p} for n, p in checks]}
    _atomic_write_json(Path(__file__).resolve().parents[1] / "trace" / f"{iso}-selftest.json", trace)
    print(f"# capacity_kernel selftest {iso} → {'🟢' if ok else '🔴'}")
    for n, p in checks:
        print(f"  {'PASS' if p else 'FAIL'}  {n}")
    return 0 if ok else 1


def _cmd_estimate(args) -> int:
    spec = load_spec(_load_json(Path(args.spec)))
    print(json.dumps(estimate(spec), ensure_ascii=False, indent=2))
    return 0


def _cmd_judge(args) -> int:
    spec = load_spec(_load_json(Path(args.spec)))
    budgets = _load_json(Path(args.budgets)) if args.budgets else {}
    verdict = judge(spec, budgets)
    if args.loop:
        state_path = Path(args.state_dir) / f"{args.loop}.json"
        state = _load_json(state_path) if state_path.exists() else {}
        _atomic_write_json(state_path, advance(state, args.iso or "NO-ISO", verdict))
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["verdict"] == "FEASIBLE" else 3


def _cmd_scorecard(args) -> int:
    spec = load_spec(_load_json(Path(args.spec)))
    budgets = _load_json(Path(args.budgets)) if args.budgets else {}
    dims = [d.strip() for d in args.dims.split(",")] if args.dims else None
    print(json.dumps(scorecard_from_judge(judge(spec, budgets), dims), ensure_ascii=False, indent=2))
    return 0


def _cmd_state(args) -> int:
    state_path = Path(args.state_dir) / f"{args.loop}.json"
    if not state_path.exists():
        print(f"[no-loop-state: {args.loop}]")
        return 1
    print(_render_state_snapshot(_load_json(state_path)))
    return 0


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="capacity_kernel",
                                 description="deterministic AI-Agent capacity estimator + feasibility judge (deterministic)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_self = sub.add_parser("selftest", help="reproduce the DR worked example + assert judge discrimination")
    p_self.add_argument("--iso", required=True, help="deterministic timestamp (no datetime.now)")
    p_est = sub.add_parser("estimate", help="compute the five DR metrics for a spec")
    p_est.add_argument("--spec", required=True)
    p_est.add_argument("--iso", help="optional timestamp (unused; parity)")
    p_jud = sub.add_parser("judge", help="emit a FEASIBLE/INFEASIBLE verdict (exit 0/3) vs budgets")
    p_jud.add_argument("--spec", required=True)
    p_jud.add_argument("--budgets", help="budgets JSON (omit = all criteria informational)")
    p_jud.add_argument("--loop", help="record this verdict into loop-state <loop>.json")
    p_jud.add_argument("--iso", help="iteration timestamp (when --loop)")
    p_jud.add_argument("--state-dir", default=str(_default_state_dir()))
    p_st = sub.add_parser("state", help="print a bounded loop-state snapshot (DCI injection source)")
    p_st.add_argument("--loop", required=True)
    p_st.add_argument("--state-dir", default=str(_default_state_dir()))
    p_sc = sub.add_parser("scorecard", help="project the judge to a /self-correcting-loop runnable scorecard")
    p_sc.add_argument("--spec", required=True)
    p_sc.add_argument("--budgets", help="budgets JSON (the criteria with budgets are the projectable dims)")
    p_sc.add_argument("--dims", help="comma-separated criterion ids (default: all constrained); keys must == loop rubric ids")
    p_sc.add_argument("--iso", help="optional timestamp (parity)")

    a = ap.parse_args(argv[1:])
    try:
        if a.cmd == "selftest":
            return _cmd_selftest(a.iso)
        if a.cmd == "estimate":
            return _cmd_estimate(a)
        if a.cmd == "judge":
            return _cmd_judge(a)
        if a.cmd == "state":
            return _cmd_state(a)
        if a.cmd == "scorecard":
            return _cmd_scorecard(a)
    except SpecError as e:
        print(f"✗ input error (fail-loud): {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
