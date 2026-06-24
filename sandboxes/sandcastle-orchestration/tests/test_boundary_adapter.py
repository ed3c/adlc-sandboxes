"""boundary_adapter behavior tests — the deterministic Path B test pyramid.

The adapter is a PURE function of (rip_result, iso, source_path): no Docker, no network, no
datetime.now(). These test BEHAVIOR through the public interface (sum_tokens / verdict_from_exit /
landed_from_host_git / container_isolation_from_iterations / build_record / assert_well_formed /
_main), not implementation detail. The probabilistic TS RIP run (Path A) is NOT tested here — it is
agent-non-deterministic and mocking it would only prove interface wiring, not runtime behavior.

This module runs NO subprocess (no PROJECT_ROOT env dance needed). The adapter is imported directly
(sys.path.insert), not via importlib. The observation-record is a plain dict (no @dataclass).

Related docs:
- Implementation: sandboxes/sandcastle-orchestration/src/boundary_adapter.py
- Real captured shape: sandboxes/sandcastle-orchestration/tests/fixtures/result.sample.json
- This sandbox's RUN.md (the real live transcript the frozen fixture comes from)
"""
import json
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC))

import boundary_adapter as ba  # noqa: E402

_FIX = Path(__file__).resolve().parent / "fixtures"

# The Boundary Artifact contract: the EXACT top-level key set slice 04 consumes. Locked here.
EXPECTED_TOP_KEYS = {
    "schema", "iso", "source_result", "composition",
    "capabilities_exercised", "agent_runs", "containment",
}


def _iteration(inp=1, cc=10, cr=100, out=5):
    return {
        "sessionId": "x",
        "usage": {
            "inputTokens": inp,
            "cacheCreationInputTokens": cc,
            "cacheReadInputTokens": cr,
            "outputTokens": out,
        },
    }


def _synth_result(**overrides):
    """Hand-built synthetic rip-result in the REAL composition shape (for T1-T3, no RIP run needed)."""
    base = {
        "schema": "sandcastle-rip/v0",
        "composition": "sandcastle-head-run + host-git + host-exec-gate",
        "seed_sha": "seed00",
        "implement": {
            "iterations": [_iteration(1, 10, 100, 5), _iteration(2, 20, 200, 7)],
            "completionSignal": "<promise>COMPLETE</promise>",
            "stdout": "fixed it",
            "commits": [],
            "branch": "main",
        },
        "exec_gate": {"command": "node --test", "exit": 0, "passed": True},
        "review": {
            "iterations": [_iteration(1, 5, 50, 3)],
            "completionSignal": "<promise>COMPLETE</promise>",
            "stdout": "looks good",
            "commits": [],
            "branch": "main",
        },
        "host_git": {"branch": "agent/fix-sum", "commit": "deadbeef", "landed": True},
        "target_repo": "/tmp/sandcastle-target",
    }
    base.update(overrides)
    return base


# ── T1 — Unit (extraction helpers over small inline dicts; pure, no IO) ────────


def test_sum_tokens_sums_across_iterations():
    iters = [_iteration(1, 10, 100, 5), _iteration(2, 20, 200, 7)]
    assert ba.sum_tokens(iters) == {"input": 3, "cache_creation": 30, "cache_read": 300, "output": 12}


def test_sum_tokens_empty_iterations_is_all_zero():
    assert ba.sum_tokens([]) == {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}


def test_sum_tokens_missing_usage_fails_loud():
    with pytest.raises(ba.ResultError):
        ba.sum_tokens([{"sessionId": "x"}])  # no usage dict


def test_sum_tokens_non_int_usage_fails_loud():
    bad = [{"usage": {"inputTokens": "1", "cacheCreationInputTokens": 0,
                      "cacheReadInputTokens": 0, "outputTokens": 0}}]
    with pytest.raises(ba.ResultError):
        ba.sum_tokens(bad)


def test_verdict_from_exit_zero_is_pass():
    assert ba.verdict_from_exit(0) == "pass"


@pytest.mark.parametrize("code", [1, 2, 137])
def test_verdict_from_exit_nonzero_is_fail(code):
    assert ba.verdict_from_exit(code) == "fail"


def test_verdict_from_exit_non_int_fails_loud():
    with pytest.raises(ba.ResultError):
        ba.verdict_from_exit("0")


def test_verdict_from_exit_bool_rejected_not_coerced():
    # True == 1 in python — must NOT be silently treated as an int exit code
    with pytest.raises(ba.ResultError):
        ba.verdict_from_exit(True)


def test_landed_true_when_flag_and_commit_present():
    assert ba.landed_from_host_git({"branch": "b", "commit": "abc123", "landed": True}) is True


def test_landed_false_when_flag_set_but_commit_empty():
    # a landed-flag without a commit sha is not a landing (Slop #18: claim without evidence)
    assert ba.landed_from_host_git({"branch": "b", "commit": "", "landed": True}) is False


def test_landed_false_when_flag_false():
    assert ba.landed_from_host_git({"branch": "b", "commit": "abc123", "landed": False}) is False


def test_landed_non_bool_flag_fails_loud():
    with pytest.raises(ba.ResultError):
        ba.landed_from_host_git({"branch": "b", "commit": "abc123", "landed": "yes"})


def test_container_isolation_true_when_iterations_present():
    assert ba.container_isolation_from_iterations([_iteration()]) is True


def test_container_isolation_false_when_no_iterations():
    assert ba.container_isolation_from_iterations([]) is False


def test_container_isolation_non_list_fails_loud():
    with pytest.raises(ba.ResultError):
        ba.container_isolation_from_iterations("nope")


# ── T2 — Wiring (read a result.json file → record dict; real file IO via tmp_path) ──


def test_load_json_reads_result_file(tmp_path):
    p = tmp_path / "result.json"
    p.write_text(json.dumps(_synth_result()), encoding="utf-8")
    assert ba._load_json(p) == _synth_result()


def test_load_json_missing_file_fails_loud(tmp_path):
    with pytest.raises(ba.ResultError, match="not found"):
        ba._load_json(tmp_path / "nope.json")


def test_load_json_invalid_json_fails_loud(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{bad", encoding="utf-8")
    with pytest.raises(ba.ResultError, match="invalid JSON"):
        ba._load_json(p)


def test_build_record_from_loaded_file_produces_record(tmp_path):
    p = tmp_path / "result.json"
    p.write_text(json.dumps(_synth_result()), encoding="utf-8")
    rec = ba.build_record(ba._load_json(p), "2026-06-24", str(p))
    assert rec["schema"] == ba.SCHEMA
    assert rec["capabilities_exercised"]["container_isolation"] is True
    assert rec["capabilities_exercised"]["exec_gate"]["verdict"] == "pass"
    assert rec["capabilities_exercised"]["branch_merge_back_outcome"]["landed"] is True
    assert rec["capabilities_exercised"]["multi_stage"] == {"implement": True, "review": True}


def test_validate_result_shape_missing_keys_fails_loud():
    with pytest.raises(ba.ResultError, match="signature keys"):
        ba.validate_result_shape({})


def test_build_record_records_provenance():
    rec = ba.build_record(_synth_result(), "2026-06-24", "some/path.json")
    assert rec["iso"] == "2026-06-24"          # no datetime.now — provenance is the --iso flag
    assert rec["source_result"] == "some/path.json"


def test_build_record_review_null_marks_review_false_and_one_agent_run():
    rec = ba.build_record(_synth_result(review=None), "2026-06-24", "p")
    assert rec["capabilities_exercised"]["multi_stage"]["review"] is False
    assert [r["stage"] for r in rec["agent_runs"]] == ["implement"]


def test_build_record_exec_gate_fail_when_nonzero_exit():
    r = _synth_result(exec_gate={"command": "node --test", "exit": 1, "passed": False})
    rec = ba.build_record(r, "2026-06-24", "p")
    assert rec["capabilities_exercised"]["exec_gate"]["verdict"] == "fail"


def test_build_record_empty_implement_iterations_marks_isolation_false():
    impl = {"iterations": [], "completionSignal": None}
    rec = ba.build_record(_synth_result(implement=impl), "2026-06-24", "p")
    assert rec["capabilities_exercised"]["container_isolation"] is False
    assert rec["agent_runs"][0]["tokens"] == {"input": 0, "cache_creation": 0,
                                              "cache_read": 0, "output": 0}


# ── T3 — Contract (lock the observation-record schema — the Boundary Artifact slice 04 consumes) ──


def test_record_has_exactly_the_contract_top_keys():
    rec = ba.build_record(_synth_result(), "2026-06-24", "p")
    assert set(rec.keys()) == EXPECTED_TOP_KEYS


def test_schema_id_is_versioned_constant():
    rec = ba.build_record(_synth_result(), "2026-06-24", "p")
    assert rec["schema"] == "sandcastle-observation-record/v1"  # slice 04 byte-matches this


def test_capabilities_exercised_subkeys_locked():
    caps = ba.build_record(_synth_result(), "2026-06-24", "p")["capabilities_exercised"]
    assert set(caps.keys()) == {
        "container_isolation", "exec_gate", "branch_merge_back_outcome", "multi_stage"
    }
    assert set(caps["exec_gate"].keys()) == {"ran", "verdict", "command", "exit"}
    assert set(caps["branch_merge_back_outcome"].keys()) == {"landed", "branch", "commit", "via"}
    assert set(caps["multi_stage"].keys()) == {"implement", "review"}


def test_agent_run_shape_locked():
    run = ba.build_record(_synth_result(), "2026-06-24", "p")["agent_runs"][0]
    assert set(run.keys()) == {"stage", "iterations", "completion_signal", "tokens"}
    assert set(run["tokens"].keys()) == {"input", "cache_creation", "cache_read", "output"}


def test_containment_invariant_field_always_false():
    rec = ba.build_record(_synth_result(), "2026-06-24", "p")
    assert rec["containment"]["host_repo_touched"] is False
    assert set(rec["containment"].keys()) == {"target_repo", "host_repo_touched"}


def test_exec_gate_verdict_is_one_of_enum():
    rec = ba.build_record(_synth_result(), "2026-06-24", "p")
    assert rec["capabilities_exercised"]["exec_gate"]["verdict"] in ("pass", "fail")


def test_record_json_roundtrips_byte_stable():
    rec = ba.build_record(_synth_result(), "2026-06-24", "p")
    assert json.loads(json.dumps(rec, sort_keys=True)) == rec


def test_to_dict_is_deterministic_same_input_same_record():
    a = ba.build_record(_synth_result(), "2026-06-24", "p")
    b = ba.build_record(_synth_result(), "2026-06-24", "p")
    assert a == b


def test_assert_well_formed_accepts_a_valid_record():
    ba.assert_well_formed(ba.build_record(_synth_result(), "2026-06-24", "p"))  # no raise


def test_assert_well_formed_rejects_touched_host_repo():
    rec = ba.build_record(_synth_result(), "2026-06-24", "p")
    rec["containment"]["host_repo_touched"] = True
    with pytest.raises(ba.ResultError, match="host_repo_touched"):
        ba.assert_well_formed(rec)


# ── T4 — Runtime E2E (against the FROZEN REAL fixture; zero MagicMock, real file + serialization) ──


def test_real_sample_fixture_exists():
    assert (_FIX / "result.sample.json").exists()


def test_adapter_on_real_frozen_result_well_formed():
    result = ba._load_json(_FIX / "result.sample.json")
    rec = ba.build_record(result, "2026-06-24", "tests/fixtures/result.sample.json")
    ba.assert_well_formed(rec)  # real dump, real dict, real shape — must not raise
    caps = rec["capabilities_exercised"]
    # the real run: implement ran in-container, gate passed, host-git landed the branch
    assert caps["container_isolation"] is True
    assert caps["exec_gate"]["verdict"] == "pass"
    assert caps["branch_merge_back_outcome"]["landed"] is True
    assert caps["branch_merge_back_outcome"]["branch"] == "agent/fix-sum"
    assert caps["multi_stage"] == {"implement": True, "review": True}


def test_real_fixture_token_totals_match_dump():
    # the real fixture's implement stage has one iteration with these exact usage counters
    rec = ba.build_record(ba._load_json(_FIX / "result.sample.json"), "2026-06-24", "p")
    impl = next(r for r in rec["agent_runs"] if r["stage"] == "implement")
    assert impl["tokens"] == {"input": 1, "cache_creation": 190, "cache_read": 22579, "output": 32}


def test_emit_subcommand_prints_well_formed_record(tmp_path, monkeypatch, capsys):
    # real _main entry, real frozen fixture, real serialization; redirect trace writes into tmp_path
    monkeypatch.setattr(ba, "_TRACE", tmp_path / "trace")
    rc = ba._main([
        "boundary_adapter", "emit",
        "--result", str(_FIX / "result.sample.json"), "--iso", "2026-06-24",
    ])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    assert set(printed.keys()) == EXPECTED_TOP_KEYS
    assert printed["schema"] == "sandcastle-observation-record/v1"
    assert (tmp_path / "trace" / "2026-06-24-observation-record.json").exists()


def test_emit_malformed_input_fails_loud(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{bad", encoding="utf-8")
    rc = ba._main(["boundary_adapter", "emit", "--result", str(p), "--iso", "2026-06-24"])
    assert rc == 1
    assert "fail-loud" in capsys.readouterr().err


def test_selftest_exits_zero_against_frozen_fixture(tmp_path, monkeypatch, capsys):
    # this IS what the fold-in gate runtime tier runs (runtime_trace_cmd)
    monkeypatch.setattr(ba, "_TRACE", tmp_path / "trace")
    rc = ba._main(["boundary_adapter", "selftest", "--iso", "2026-06-24"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "🟢" in out
    assert "FAIL" not in out
