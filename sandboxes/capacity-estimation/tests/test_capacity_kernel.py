"""
capacity_kernel behavior tests — the deterministic AI-Agent capacity estimator + feasibility judge.

The kernel is a PURE function of (spec, budgets): no Ollama, no network, no datetime.now(). These
test BEHAVIOR through the public interface (estimate / judge / load_spec / advance / CLI), not
implementation detail. Every metric reproduces the DR worked example exactly, every judge branch is
exercised, and the discrimination cases (a kernel that ignored a metric would mark them feasible)
are the reverse-mutant guards.

Related docs:
- Implementation: sandboxes/capacity-estimation/src/capacity_kernel.py
- Interface contract: sandboxes/capacity-estimation/SKILL.md (C1-C5)
- Source formula inventory: sandboxes/capacity-estimation/docs/dr-formula-inventory.md
"""
import copy
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC))

import capacity_kernel as ck  # noqa: E402

_FIX = _SRC / "fixtures"


def _dr_dict() -> dict:
    return copy.deepcopy(ck._load_json(_FIX / "dr-example-spec.json"))


def _dr_spec() -> ck.Spec:
    return ck.load_spec(_dr_dict())


# ── estimate: faithful reproduction of the DR §2/§5 worked example ─────────────

def test_step1_agent_qps_is_user_qps_times_n_loops():
    est = ck.estimate(_dr_spec())
    assert est["step1_amplification"]["agent_qps"] == 40        # 10 × 4
    assert est["step1_amplification"]["rpm_equiv"] == 2400


def test_step2_throughput_input_and_output_tps():
    est = ck.estimate(_dr_spec())
    assert est["step2_throughput"]["input_tps"] == 120_000      # 40 × 3000
    assert est["step2_throughput"]["output_tps"] == 20_000      # 40 × 500
    assert est["step2_throughput"]["total_tps"] == 140_000


def test_step3_weights_140gb_decimal():
    est = ck.estimate(_dr_spec())
    assert est["step3_vram"]["weights"]["gb"] == pytest.approx(140.0)   # 70B × 2 bytes


def test_step3_kv_per_token_exact_bytes():
    # 2 × L(80) × H_kv(8) × D_head(128) × precision(2) — exact int, the load-bearing formula
    assert ck.estimate(_dr_spec())["step3_vram"]["kv_per_token_bytes"] == 327_680


def test_step3_kv_total_40gib_at_batch32_4k():
    est = ck.estimate(_dr_spec())
    assert est["step3_vram"]["kv_total"]["gib"] == pytest.approx(40.0)  # 327680 × 4096 × 32 / 2^30


def test_step3_cards_needed_is_ceil_of_total_over_card():
    # total ≈ 182.95 GB-decimal; /80 = 2.29 → ceil 3 cards
    assert ck.estimate(_dr_spec())["step3_vram"]["cards_needed"] == 3


def test_step5_rag_raw_and_indexed_match_dr():
    est = ck.estimate(_dr_spec())
    assert est["step5_rag"]["raw"]["gb"] == pytest.approx(122.88)        # 10M × 3072 × 4
    assert est["step5_rag"]["with_index"]["gb"] == pytest.approx(184.32) # × 1.5


def test_both_units_reported_to_surface_dr_gb_gib_inconsistency():
    # the kernel keeps exact bytes + BOTH conversions (mirror-finding: DR mixes GB/GiB)
    w = ck.estimate(_dr_spec())["step3_vram"]["weights"]
    assert w["bytes"] == 140_000_000_000
    assert w["gb"] == pytest.approx(140.0) and w["gib"] == pytest.approx(130.385, abs=0.01)


# ── estimate: the §5 KV formula's extra dimensions (S / B / TP) actually bind ──

def test_tensor_parallel_divides_kv_cache():
    d = _dr_dict(); d["serving"]["tensor_parallel"] = 2
    halved = ck.estimate(ck.load_spec(d))["step3_vram"]["kv_total"]["gib"]
    assert halved == pytest.approx(20.0)        # 40 GiB / TP(2)


def test_batch_size_scales_kv_cache_linearly():
    d = _dr_dict(); d["serving"]["batch_size"] = 64
    doubled = ck.estimate(ck.load_spec(d))["step3_vram"]["kv_total"]["gib"]
    assert doubled == pytest.approx(80.0)       # batch 32 → 64 doubles KV


def test_fp8_precision_halves_weights_and_kv():
    d = _dr_dict(); d["model"]["precision_bytes"] = 1   # FP8
    est = ck.estimate(ck.load_spec(d))
    assert est["step3_vram"]["weights"]["gb"] == pytest.approx(70.0)
    assert est["step3_vram"]["kv_per_token_bytes"] == 163_840


# ── judge: FEASIBLE / INFEASIBLE branches + binding constraint + DR lever ──────

def _generous_budgets() -> dict:
    return {"cards_available": 3, "backend_rpm_limit": 3000, "tpm_budget": 9_000_000, "host_ram_gb": 256}


def test_judge_feasible_when_all_budgets_met():
    v = ck.judge(_dr_spec(), _generous_budgets())
    assert v["verdict"] == "FEASIBLE"
    assert v["binding"] == []


def test_judge_infeasible_vram_is_the_reverse_mutant_guard():
    # squeeze cards 3→2: the DR example's 180GB needs 3×80GB → vram MUST bind. A kernel that ignored
    # cards_needed would stay FEASIBLE here (the discriminating self-check).
    v = ck.judge(_dr_spec(), {"cards_available": 2})
    assert v["verdict"] == "INFEASIBLE"
    assert v["binding"] == ["vram_concurrency"]


def test_binding_vram_carries_macro_and_micro_levers():
    v = ck.judge(_dr_spec(), {"cards_available": 2})
    crit = next(c for c in v["criteria"] if c["name"] == "vram_concurrency")
    assert crit["status"] == "BINDING"
    assert "PagedAttention" in crit["lever"]["micro"]          # micro code lever
    assert "張量並行" in crit["lever"]["macro"] or "TP" in crit["lever"]["macro"]  # macro arch lever


def test_judge_infeasible_throughput_binds_when_tpm_too_low():
    v = ck.judge(_dr_spec(), {"tpm_budget": 1_000_000})        # need 8.4M tokens/min
    assert v["verdict"] == "INFEASIBLE"
    assert "token_throughput_tpm" in v["binding"]


def test_judge_infeasible_rpm_binds_when_backend_too_low():
    v = ck.judge(_dr_spec(), {"backend_rpm_limit": 100})       # need 2400 req/min
    assert v["binding"] == ["amplification_rpm"]


def test_judge_infeasible_rag_binds_when_host_ram_too_low():
    v = ck.judge(_dr_spec(), {"host_ram_gb": 64})              # need 184.32 GB
    assert v["binding"] == ["rag_ram"]


def test_prefix_cache_below_breakeven_binds():
    d = _dr_dict(); d["prefix_cache"] = {"hit_rate": 0.1, "breakeven": 0.30}
    v = ck.judge(ck.load_spec(d), {})
    assert v["verdict"] == "INFEASIBLE"
    assert v["binding"] == ["prefix_cache_breakeven"]


def test_prefix_cache_above_breakeven_passes():
    d = _dr_dict(); d["prefix_cache"] = {"hit_rate": 0.5, "breakeven": 0.30}
    v = ck.judge(ck.load_spec(d), {})
    assert v["verdict"] == "FEASIBLE"


def test_unbudgeted_criterion_is_not_constrained_never_fails():
    # empty budgets + no prefix hit_rate → every criterion informational → vacuously FEASIBLE
    v = ck.judge(_dr_spec(), {})
    assert v["verdict"] == "FEASIBLE"
    assert v["evaluated"] == 0
    assert set(v["not_constrained"]) == {
        "amplification_rpm", "token_throughput_tpm", "vram_concurrency",
        "prefix_cache_breakeven", "rag_ram", "spec_decode_batch_ceiling",
    }


def test_multiple_binding_constraints_all_reported():
    v = ck.judge(_dr_spec(), {"cards_available": 1, "host_ram_gb": 10})
    assert v["verdict"] == "INFEASIBLE"
    assert set(v["binding"]) == {"vram_concurrency", "rag_ram"}


# ── the DR knowledge base is actually encoded (completeness of the absorption) ─

def test_vector_index_tradeoff_table_has_all_four_dr_rows():
    names = [r["index"] for r in ck.VECTOR_INDEX_TABLE]
    assert any("SQ8" in n for n in names)
    assert any("PQ" in n for n in names)
    assert any("DiskANN" in n for n in names)
    assert any("float32" in n for n in names)


def test_levers_cover_every_judge_criterion_domain():
    for key in ("amplification", "token_throughput", "vram_concurrency", "prefix_cache", "rag_ram", "latency"):
        assert key in ck.LEVERS
        assert ck.LEVERS[key]["macro"] and ck.LEVERS[key]["micro"]


def test_spec_decode_batch_ceiling_boundary_encoded():
    # DR §4 boundary: speculative decoding degrades past batch 32 — encoded as a constant + in the lever
    assert ck.SPEC_DECODE_BATCH_CEILING == 32
    assert "32" in ck.LEVERS["latency"]["micro"]


# ── ENHANCEMENT: the DR §2 vector-index table is ACTIVELY consumed (not inert) ─────

def test_index_recommendation_default_is_hnsw_float32():
    # no recall/latency target → the DR default index
    rec = ck.estimate(_dr_spec())["step5_rag"]["recommended_index"]
    assert rec["index"] == "HNSW float32"
    assert rec["ram"]["gb"] == pytest.approx(122.88 * 1.8, rel=1e-6)   # raw × mem_mult


def test_index_recommendation_recall_latency_picks_cheapest_meeting_budget():
    # recall>=0.93 ∧ p95<=10ms: DiskANN excluded by latency(30>10), PQ by recall(0.70<0.93) → cheapest = SQ8
    d = _dr_dict(); d["rag"]["recall_floor"] = 0.93; d["rag"]["p95_ms_budget"] = 10
    rec = ck.estimate(ck.load_spec(d))["step5_rag"]["recommended_index"]
    assert rec["index"] == "HNSW + SQ8 (uint8)"
    assert rec["ram"]["gb"] == pytest.approx(122.88 * 0.3, rel=1e-6)   # SQ8 ~0.3x → much less RAM (micro guidance)


def test_index_recommendation_high_recall_low_latency_forces_hnsw():
    # recall>=0.98 ∧ p95<=5ms: only HNSW float32 qualifies (highest fidelity, highest memory)
    d = _dr_dict(); d["rag"]["recall_floor"] = 0.98; d["rag"]["p95_ms_budget"] = 5
    rec = ck.estimate(ck.load_spec(d))["step5_rag"]["recommended_index"]
    assert rec["index"] == "HNSW float32"


def test_index_recommendation_none_when_unsatisfiable():
    # recall 0.999 exceeds every table row → no index satisfies → surfaced, not silently picked
    d = _dr_dict(); d["rag"]["recall_floor"] = 0.999
    rec = ck.estimate(ck.load_spec(d))["step5_rag"]["recommended_index"]
    assert rec["index"] is None and "no index" in rec["reason"]


def test_recall_floor_out_of_range_fails_loud():
    d = _dr_dict(); d["rag"]["recall_floor"] = 1.5
    with pytest.raises(ck.SpecError, match="recall_floor"):
        ck.load_spec(d)


# ── ENHANCEMENT: the DR §4 spec-decode batch-ceiling boundary is ENFORCED (not inert) ─────

def test_spec_decode_binds_above_ceiling():
    # batch 64 (>32) + architecture plans spec-decode → the DR's degradation boundary BINDS
    d = _dr_dict(); d["serving"]["batch_size"] = 64
    v = ck.judge(ck.load_spec(d), {"spec_decode_enabled": True})
    assert v["verdict"] == "INFEASIBLE"
    assert "spec_decode_batch_ceiling" in v["binding"]


def test_spec_decode_ok_at_or_below_ceiling():
    # batch 32 (== ceiling) + spec-decode planned → within the boundary, passes
    v = ck.judge(_dr_spec(), {"spec_decode_enabled": True})
    assert v["verdict"] == "FEASIBLE"


def test_spec_decode_not_constrained_when_not_enabled():
    # batch 64 but spec-decode NOT planned → no spec-decode criterion fires (informational)
    d = _dr_dict(); d["serving"]["batch_size"] = 64
    v = ck.judge(ck.load_spec(d), {})
    assert "spec_decode_batch_ceiling" in v["not_constrained"]


# ── fail-loud input defects (the issue, never silently coerced) ───────────────────

def test_missing_required_field_fails_loud():
    with pytest.raises(ck.SpecError, match="user_qps"):
        ck.load_spec({"workload": {"n_loops": 4}})


def test_negative_value_fails_loud():
    d = _dr_dict(); d["workload"]["user_qps"] = -1
    with pytest.raises(ck.SpecError):
        ck.load_spec(d)


def test_bool_value_rejected_not_coerced():
    d = _dr_dict(); d["model"]["params_billions"] = True
    with pytest.raises(ck.SpecError):
        ck.load_spec(d)


def test_breakeven_out_of_range_fails_loud():
    d = _dr_dict(); d["prefix_cache"] = {"breakeven": 1.5}
    with pytest.raises(ck.SpecError, match="breakeven"):
        ck.load_spec(d)


def test_hit_rate_out_of_range_fails_loud():
    d = _dr_dict(); d["prefix_cache"] = {"hit_rate": 2.0}
    with pytest.raises(ck.SpecError, match="hit_rate"):
        ck.load_spec(d)


def test_judge_rejects_non_dict_budgets():
    with pytest.raises(ck.SpecError):
        ck.judge(_dr_spec(), ["not", "a", "dict"])


# ── defaults applied when optional fields omitted ──────────────────────────────

def test_defaults_tp_card_vram_alpha_breakeven():
    d = _dr_dict()
    del d["serving"]["tensor_parallel"]; del d["serving"]["card_vram_gb"]; del d["rag"]["hnsw_alpha"]
    s = ck.load_spec(d)
    assert s.tensor_parallel == 1
    assert s.card_vram_gb == ck.DEFAULT_CARD_VRAM_GB
    assert s.hnsw_alpha == ck.DEFAULT_HNSW_ALPHA
    assert s.prefix_breakeven == ck.DEFAULT_PREFIX_BREAKEVEN


# ── advance: bounded loop-state tracking (judge feeding an iteration loop) ──────

def test_advance_appends_numbered_iterations_with_verdict():
    state: dict = {}
    ck.advance(state, "2026-06-24", ck.judge(_dr_spec(), {"cards_available": 2}))
    ck.advance(state, "2026-06-24", ck.judge(_dr_spec(), {"cards_available": 3}))
    assert [it["iteration"] for it in state["iterations"]] == [1, 2]
    assert state["verdict"] == "FEASIBLE"          # last verdict wins
    assert state["iterations"][0]["binding"] == ["vram_concurrency"]


# ── CLI: exit semantics (0 FEASIBLE / 3 INFEASIBLE — plugs into self-correcting-loop runnable) ──

def test_cli_judge_exit_zero_when_feasible(tmp_path):
    import json
    bud = tmp_path / "b.json"; bud.write_text(json.dumps(_generous_budgets()))
    rc = ck._main(["capacity_kernel", "judge", "--spec", str(_FIX / "dr-example-spec.json"),
                   "--budgets", str(bud)])
    assert rc == 0


def test_cli_judge_exit_three_when_infeasible(tmp_path):
    import json
    bud = tmp_path / "b.json"; bud.write_text(json.dumps({"cards_available": 1}))
    rc = ck._main(["capacity_kernel", "judge", "--spec", str(_FIX / "dr-example-spec.json"),
                   "--budgets", str(bud)])
    assert rc == 3       # distinct non-error code → a loop driver branches FEASIBLE vs INFEASIBLE


def test_cli_estimate_exits_zero():
    rc = ck._main(["capacity_kernel", "estimate", "--spec", str(_FIX / "dr-example-spec.json")])
    assert rc == 0


def test_cli_bad_spec_fails_loud_exit_one(tmp_path):
    bad = tmp_path / "bad.json"; bad.write_text('{"workload": {"user_qps": -5}}')
    rc = ck._main(["capacity_kernel", "estimate", "--spec", str(bad)])
    assert rc == 1


def test_selftest_cli_exits_zero(capsys):
    rc = ck._main(["capacity_kernel", "selftest", "--iso", "2026-06-24T00:00:00Z"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "🟢" in out and "FAIL" not in out


# ── FLEET loop-composition: scorecard projection to a /self-correcting-loop runnable scorecard ─────

def _full_budgets():
    return {"backend_rpm_limit": 3000, "tpm_budget": 9_000_000, "cards_available": 2, "host_ram_gb": 256}


def _full_spec():
    d = _dr_dict(); d["prefix_cache"] = {"hit_rate": 0.5, "breakeven": 0.30}
    return ck.load_spec(d)


def test_scorecard_keys_are_exactly_the_constrained_criteria():
    sc = ck.scorecard_from_judge(ck.judge(_full_spec(), _full_budgets()))
    assert set(sc) == {"amplification_rpm", "token_throughput_tpm", "vram_concurrency",
                       "prefix_cache_breakeven", "rag_ram"}


def test_scorecard_values_are_runnable_exit_codes():
    sc = ck.scorecard_from_judge(ck.judge(_full_spec(), _full_budgets()))
    assert all(v in (0, 1) for v in sc.values())
    assert sc["vram_concurrency"] == 1          # cards 2 < needed 3 → BINDING → exit 1 (loop focuses it)
    assert sc["amplification_rpm"] == 0 and sc["rag_ram"] == 0   # within budget → exit 0


def test_scorecard_dims_subset_keeps_keys_equal_to_rubric_ids():
    sc = ck.scorecard_from_judge(ck.judge(_full_spec(), _full_budgets()),
                                 dims=["vram_concurrency", "rag_ram"])
    assert set(sc) == {"vram_concurrency", "rag_ram"}   # exact-match contract for loop_kernel


def test_scorecard_fails_loud_on_unconstrained_dim():
    # token_throughput_tpm is NOT constrained when tpm_budget is absent → projecting it must fail loud
    with pytest.raises(ck.SpecError, match="token_throughput_tpm"):
        ck.scorecard_from_judge(ck.judge(_dr_spec(), {"cards_available": 3}),
                                dims=["token_throughput_tpm"])


def test_scorecard_projection_is_loop_kernel_compatible():
    # the projected scorecard, fed to the ACTUAL self-correcting-loop kernel + this recipe's rubric, must
    # DECIDE the same verdict capacity's own judge gave — proves real (not just documented) composition.
    import importlib.util
    import json
    lk_path = _SRC.parents[1] / "self-correcting-loop" / "src" / "loop_kernel.py"   # parents[1]=sandboxes/
    if not lk_path.is_file():
        pytest.skip("self-correcting-loop kernel not present (composition is recipe-documented)")
    spec_lk = importlib.util.spec_from_file_location("loop_kernel", lk_path)
    lk = importlib.util.module_from_spec(spec_lk)
    sys.modules["loop_kernel"] = lk          # Bug Scar #397: @dataclass + future-annotations + importlib
    spec_lk.loader.exec_module(lk)
    rubric = lk.load_rubric(json.loads(
        (_SRC.parents[0] / "recipes" / "capacity-estimation.rubric.json").read_text(encoding="utf-8")))
    verdict = ck.judge(_full_spec(), _full_budgets())
    sc = ck.scorecard_from_judge(verdict)            # keys == the 5 rubric ids
    decision = lk.decide(rubric, sc)
    # capacity INFEASIBLE (vram binds) ⟺ loop ITERATING with focus on the binding criterion
    assert (verdict["verdict"] == "INFEASIBLE") == (decision.verdict == "ITERATING")
    assert decision.focus == "vram_concurrency"
