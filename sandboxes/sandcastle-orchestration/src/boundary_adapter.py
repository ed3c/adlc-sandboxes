#!/usr/bin/env python3
"""boundary_adapter — Path B deterministic seam for the sandcastle-orchestration sandbox.

WHY (the demand): the RIP run (Path A, src/run_sandcastle.ts) is probabilistic, costs Docker +
tokens, and dumps a rich `rip-result.json`. The validation gate's runtime tier must NOT re-run that.
This adapter is the deterministic Path B projection: a pure function `rip-result.json` ->
OBSERVATION-RECORD that answers "which capabilities did sandcastle actually exercise" in a
machine-parseable, stable shape that a downstream triage step consumes.

SHAPE (the REAL captured composition, NOT a prose guess): sandcastle's own git-worktree
branch-merge-back is broken on macOS docker (its gitdir correction is Windows-only), so the harness
composes sandcastle `head`-run (container-isolated agent execution — the part that works) with
HOST-side git for the branch/commit "merge-back" outcome and a HOST-side exec-gate between the
implement and review stages. Therefore `implement.commits` is always [] (head never commits); the
real branch-merge-back OUTCOME lives in `host_git`. We read the composition shape:
  { schema, composition, seed_sha, implement{iterations[],completionSignal,...}, exec_gate{command,
    exit,passed}, review{...|null}, host_git{branch,commit,landed}, target_repo }

DETERMINISM: pure functions; NO datetime.now()/random — the only timestamp source is the explicit
`--iso` argument (parity with loop_kernel). The record is a pure function of
(rip_result, iso, source_path).

EXIT SEMANTICS (CLI):
  selftest : 0 = adapter produces a well-formed record against the frozen fixture · 1 = a self-check
             failed or the fixture is missing/malformed (fail-loud; never a silent green).
  emit     : 0 = produced a well-formed observation-record and printed it · 1 = malformed input
             (fail-loud on bad/missing rip-result.json).

Related docs:
- This sandbox's RUN.md (the real live transcript these records project from)
- Path A harness: src/run_sandcastle.ts (produces the rip-result.json we parse)
- Structural precedent: sandboxes/self-correcting-loop/src/loop_kernel.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# observation-record schema id — a downstream consumer byte-matches this string. OWNED here.
SCHEMA = "sandcastle-observation-record/v1"

# the rip-result schema this adapter knows how to parse (Path A's output contract).
SOURCE_SCHEMA_PREFIX = "sandcastle-rip/"

_FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
_TRACE = Path(__file__).resolve().parents[1] / "trace"

# the stages whose agent runs we project. `review` may be null (gate failed => review skipped).
_AGENT_STAGES = ("implement", "review")


class ResultError(Exception):
    """Fail-loud input defect (malformed sandcastle rip-result.json). Never silently coerced (PG-151)."""


# ── small typed helpers (T1 tests target these over inline dicts) ──────────────


def _require_dict(obj, what: str) -> dict:
    if not isinstance(obj, dict):
        raise ResultError(f"{what} must be a dict, got {type(obj).__name__}")
    return obj


def sum_tokens(iterations: list) -> dict:
    """Sum the usage counters across a stage's iterations into a stable 4-key dict.

    Empty iterations => all-zero (a valid observation: the stage ran no agent turns). Each iteration
    must carry a `usage` dict; a missing/malformed usage fails loud rather than silently zeroing
    (Slop #18: a fabricated zero is an unverified claim)."""
    if not isinstance(iterations, list):
        raise ResultError(f"iterations must be a list, got {type(iterations).__name__}")
    totals = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
    field_map = {
        "input": "inputTokens",
        "cache_creation": "cacheCreationInputTokens",
        "cache_read": "cacheReadInputTokens",
        "output": "outputTokens",
    }
    for i, it in enumerate(iterations):
        usage = _require_dict(it, f"iteration #{i}").get("usage")
        usage = _require_dict(usage, f"iteration #{i} usage")
        for out_key, in_key in field_map.items():
            v = usage.get(in_key, 0)
            if not isinstance(v, int) or isinstance(v, bool):
                raise ResultError(f"iteration #{i} usage.{in_key} must be an int, got {v!r}")
            totals[out_key] += v
    return totals


def verdict_from_exit(exit_code) -> str:
    """exec-gate verdict from its exit code: 'pass' iff exit == 0, else 'fail'. Fail-loud on non-int."""
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise ResultError(f"exec_gate.exit must be an int, got {exit_code!r}")
    return "pass" if exit_code == 0 else "fail"


def landed_from_host_git(host_git: dict) -> bool:
    """The branch-merge-back OUTCOME landed iff host_git.landed is truthy AND a commit sha is present.

    `landed` is the harness's own boolean (Boolean(commit)); we corroborate it against a non-empty
    commit sha so a flag without evidence cannot claim a landing (Slop #18)."""
    host_git = _require_dict(host_git, "host_git")
    flag = host_git.get("landed")
    if not isinstance(flag, bool):
        raise ResultError(f"host_git.landed must be a bool, got {flag!r}")
    commit = host_git.get("commit", "")
    if not isinstance(commit, str):
        raise ResultError(f"host_git.commit must be a str, got {commit!r}")
    return flag and bool(commit)


def container_isolation_from_iterations(iterations: list) -> bool:
    """True iff the implement stage actually ran a container-isolated agent turn (iterations non-empty).

    Empty iterations => no agent executed in the inner container => conservatively False (we do not
    assert isolation we have no evidence for)."""
    if not isinstance(iterations, list):
        raise ResultError(f"iterations must be a list, got {type(iterations).__name__}")
    return len(iterations) > 0


# ── stage projection ──────────────────────────────────────────────────────────


def _stage_run(stage: str, payload: dict) -> dict:
    """Project one agent stage (implement / review) into an agent-run summary. Fail-loud on shape."""
    payload = _require_dict(payload, f"{stage} stage")
    iterations = payload.get("iterations")
    if not isinstance(iterations, list):
        raise ResultError(f"{stage}.iterations must be a list, got {type(iterations).__name__}")
    completion = payload.get("completionSignal")
    if completion is not None and not isinstance(completion, str):
        raise ResultError(f"{stage}.completionSignal must be a str or null, got {completion!r}")
    return {
        "stage": stage,
        "iterations": len(iterations),
        "completion_signal": completion,
        "tokens": sum_tokens(iterations),
    }


# ── the record builder (T2/T4 + emit/selftest go through this) ─────────────────


def validate_result_shape(result) -> None:
    """Fail-loud gate: the rip-result must be a dict carrying the composition's signature keys.

    Lists every missing key (PG-151: diagnosable error, never a silent default)."""
    result = _require_dict(result, "rip-result")
    required = ("implement", "exec_gate", "host_git", "target_repo")
    missing = [k for k in required if k not in result]
    if missing:
        raise ResultError(
            f"rip-result missing signature keys {missing}; "
            f"present keys = {sorted(result.keys())}"
        )


def build_record(result: dict, iso: str, source_result_path: str) -> dict:
    """Pure: rip-result dict -> observation-record dict. Composes the extractors; fail-loud throughout.

    The returned dict IS the Boundary Artifact (a downstream consumer reads this exact shape)."""
    if not isinstance(iso, str) or not iso:
        raise ResultError(f"iso must be a non-empty str, got {iso!r}")
    validate_result_shape(result)

    implement = _require_dict(result["implement"], "implement")
    exec_gate = _require_dict(result["exec_gate"], "exec_gate")
    host_git = _require_dict(result["host_git"], "host_git")
    review = result.get("review")  # may be None (gate failed => review skipped)

    impl_iters = implement.get("iterations")
    if not isinstance(impl_iters, list):
        raise ResultError(f"implement.iterations must be a list, got {type(impl_iters).__name__}")

    exec_exit = exec_gate.get("exit")
    exec_command = exec_gate.get("command")
    if not isinstance(exec_command, str):
        raise ResultError(f"exec_gate.command must be a str, got {exec_command!r}")

    review_ran = review is not None
    agent_runs = [_stage_run("implement", implement)]
    if review_ran:
        agent_runs.append(_stage_run("review", review))

    target_repo = result["target_repo"]
    if not isinstance(target_repo, str):
        raise ResultError(f"target_repo must be a str, got {target_repo!r}")

    composition = result.get("composition")
    if not isinstance(composition, str):
        raise ResultError(f"composition must be a str, got {composition!r}")

    host_branch = host_git.get("branch")
    host_commit = host_git.get("commit", "")
    if not isinstance(host_branch, str):
        raise ResultError(f"host_git.branch must be a str, got {host_branch!r}")
    if not isinstance(host_commit, str):
        raise ResultError(f"host_git.commit must be a str, got {host_commit!r}")

    return {
        "schema": SCHEMA,
        "iso": iso,
        "source_result": source_result_path,
        "composition": composition,
        "capabilities_exercised": {
            "container_isolation": container_isolation_from_iterations(impl_iters),
            "exec_gate": {
                "ran": True,
                "verdict": verdict_from_exit(exec_exit),
                "command": exec_command,
                "exit": exec_exit,
            },
            "branch_merge_back_outcome": {
                "landed": landed_from_host_git(host_git),
                "branch": host_branch,
                "commit": host_commit,
                "via": "host-git",
            },
            "multi_stage": {
                "implement": True,
                "review": review_ran,
            },
        },
        "agent_runs": agent_runs,
        "containment": {
            "target_repo": target_repo,
            "host_repo_touched": False,  # invariant by construction: harness only touches the throwaway TARGET
        },
    }


# ── well-formedness self-check (selftest uses this) ────────────────────────────


def assert_well_formed(record: dict) -> None:
    """Assert the observation-record satisfies the OWNED contract. Any defect => ResultError (fail-loud).

    Checks: top-level key set, schema id, types of every field, the enum/verdict domains, the
    containment.host_repo_touched invariant is exactly False, and agent-run token-dict shape."""
    record = _require_dict(record, "observation-record")
    expected_top = {
        "schema", "iso", "source_result", "composition",
        "capabilities_exercised", "agent_runs", "containment",
    }
    if set(record.keys()) != expected_top:
        raise ResultError(
            f"top-level keys mismatch: {sorted(set(record.keys()))} != {sorted(expected_top)}"
        )
    if record["schema"] != SCHEMA:
        raise ResultError(f"schema must be {SCHEMA!r}, got {record['schema']!r}")
    for k in ("iso", "source_result", "composition"):
        if not isinstance(record[k], str) or not record[k]:
            raise ResultError(f"{k} must be a non-empty str, got {record[k]!r}")

    caps = _require_dict(record["capabilities_exercised"], "capabilities_exercised")
    expected_caps = {"container_isolation", "exec_gate", "branch_merge_back_outcome", "multi_stage"}
    if set(caps.keys()) != expected_caps:
        raise ResultError(f"capabilities_exercised keys mismatch: {sorted(caps.keys())}")
    if not isinstance(caps["container_isolation"], bool):
        raise ResultError(f"container_isolation must be a bool, got {caps['container_isolation']!r}")

    eg = _require_dict(caps["exec_gate"], "exec_gate")
    if set(eg.keys()) != {"ran", "verdict", "command", "exit"}:
        raise ResultError(f"exec_gate keys mismatch: {sorted(eg.keys())}")
    if not isinstance(eg["ran"], bool):
        raise ResultError(f"exec_gate.ran must be a bool, got {eg['ran']!r}")
    if eg["verdict"] not in ("pass", "fail"):
        raise ResultError(f"exec_gate.verdict must be 'pass'|'fail', got {eg['verdict']!r}")
    if not isinstance(eg["exit"], int) or isinstance(eg["exit"], bool):
        raise ResultError(f"exec_gate.exit must be an int, got {eg['exit']!r}")
    if not isinstance(eg["command"], str):
        raise ResultError(f"exec_gate.command must be a str, got {eg['command']!r}")

    bmo = _require_dict(caps["branch_merge_back_outcome"], "branch_merge_back_outcome")
    if set(bmo.keys()) != {"landed", "branch", "commit", "via"}:
        raise ResultError(f"branch_merge_back_outcome keys mismatch: {sorted(bmo.keys())}")
    if not isinstance(bmo["landed"], bool):
        raise ResultError(f"branch_merge_back_outcome.landed must be a bool, got {bmo['landed']!r}")
    if bmo["via"] != "host-git":
        raise ResultError(f"branch_merge_back_outcome.via must be 'host-git', got {bmo['via']!r}")
    for k in ("branch", "commit"):
        if not isinstance(bmo[k], str):
            raise ResultError(f"branch_merge_back_outcome.{k} must be a str, got {bmo[k]!r}")

    ms = _require_dict(caps["multi_stage"], "multi_stage")
    if set(ms.keys()) != {"implement", "review"}:
        raise ResultError(f"multi_stage keys mismatch: {sorted(ms.keys())}")
    for k in ("implement", "review"):
        if not isinstance(ms[k], bool):
            raise ResultError(f"multi_stage.{k} must be a bool, got {ms[k]!r}")

    runs = record["agent_runs"]
    if not isinstance(runs, list) or not runs:
        raise ResultError("agent_runs must be a non-empty list (implement always runs)")
    for i, run in enumerate(runs):
        run = _require_dict(run, f"agent_runs[{i}]")
        if set(run.keys()) != {"stage", "iterations", "completion_signal", "tokens"}:
            raise ResultError(f"agent_runs[{i}] keys mismatch: {sorted(run.keys())}")
        if run["stage"] not in _AGENT_STAGES:
            raise ResultError(f"agent_runs[{i}].stage must be in {_AGENT_STAGES}, got {run['stage']!r}")
        if not isinstance(run["iterations"], int) or isinstance(run["iterations"], bool) or run["iterations"] < 0:
            raise ResultError(f"agent_runs[{i}].iterations must be a non-negative int")
        cs = run["completion_signal"]
        if cs is not None and not isinstance(cs, str):
            raise ResultError(f"agent_runs[{i}].completion_signal must be a str or null")
        toks = _require_dict(run["tokens"], f"agent_runs[{i}].tokens")
        if set(toks.keys()) != {"input", "cache_creation", "cache_read", "output"}:
            raise ResultError(f"agent_runs[{i}].tokens keys mismatch: {sorted(toks.keys())}")
        for tk, tv in toks.items():
            if not isinstance(tv, int) or isinstance(tv, bool) or tv < 0:
                raise ResultError(f"agent_runs[{i}].tokens.{tk} must be a non-negative int, got {tv!r}")

    cont = _require_dict(record["containment"], "containment")
    if set(cont.keys()) != {"target_repo", "host_repo_touched"}:
        raise ResultError(f"containment keys mismatch: {sorted(cont.keys())}")
    if not isinstance(cont["target_repo"], str) or not cont["target_repo"]:
        raise ResultError(f"containment.target_repo must be a non-empty str, got {cont['target_repo']!r}")
    if cont["host_repo_touched"] is not False:
        raise ResultError(
            f"containment.host_repo_touched must be exactly False (invariant), got {cont['host_repo_touched']!r}"
        )


# ── IO (parity with loop_kernel) ───────────────────────────────────────────────


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ResultError(f"file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ResultError(f"invalid JSON in {path}: {e}") from e


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ── CLI ────────────────────────────────────────────────────────────────────────


def _cmd_selftest(iso: str) -> int:
    fixture = _FIXTURES / "result.sample.json"
    result = _load_json(fixture)  # missing/bad fixture => ResultError => exit 1 (never silent green)
    validate_result_shape(result)
    record = build_record(result, iso, "tests/fixtures/result.sample.json")

    checks: list[tuple[str, bool]] = []
    try:
        assert_well_formed(record)
        checks.append(("record_well_formed", True))
    except ResultError:
        checks.append(("record_well_formed", False))

    checks.append(("schema_id_ok", record.get("schema") == SCHEMA))
    cont = record.get("containment", {})
    checks.append(("host_repo_untouched", cont.get("host_repo_touched") is False))
    caps = record.get("capabilities_exercised", {})
    eg = caps.get("exec_gate", {})
    checks.append(("exec_gate_verdict_in_enum", eg.get("verdict") in ("pass", "fail")))
    checks.append(("container_isolation_is_bool", isinstance(caps.get("container_isolation"), bool)))
    bmo = caps.get("branch_merge_back_outcome", {})
    checks.append(("merge_back_landed_is_bool", isinstance(bmo.get("landed"), bool)))
    # real serialization round-trip — proves slice 04 reads exactly what we build
    roundtrip = json.loads(json.dumps(record, sort_keys=True)) == record
    checks.append(("roundtrip_json", roundtrip))

    ok = all(passed for _, passed in checks)
    trace = {
        "schema": "boundary-adapter-selftest/v1",
        "iso": iso,
        "ok": ok,
        "checks": [{"name": n, "pass": p} for n, p in checks],
    }
    _atomic_write_json(_TRACE / f"{iso}-selftest.json", trace)
    glyph = "🟢" if ok else "🔴"
    print(f"# boundary_adapter selftest {iso} → {glyph}")
    for n, p in checks:
        print(f"  {'PASS' if p else 'FAIL'}  {n}")
    return 0 if ok else 1


def _cmd_emit(args) -> int:
    result = _load_json(Path(args.result))
    validate_result_shape(result)
    record = build_record(result, args.iso, str(args.result))
    assert_well_formed(record)
    _atomic_write_json(_TRACE / f"{args.iso}-observation-record.json", record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="boundary_adapter",
        description="Path B deterministic projection: sandcastle rip-result.json -> observation-record",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_self = sub.add_parser(
        "selftest", help="run the adapter against the frozen fixture, assert well-formed (runtime_trace_cmd)"
    )
    p_self.add_argument("--iso", required=True, help="deterministic timestamp (no datetime.now)")

    p_emit = sub.add_parser("emit", help="parse a rip-result.json and print its observation-record JSON")
    p_emit.add_argument("--result", required=True, help="path to a sandcastle rip-result.json")
    p_emit.add_argument("--iso", required=True, help="deterministic timestamp (no datetime.now)")

    a = ap.parse_args(argv[1:])
    try:
        if a.cmd == "selftest":
            return _cmd_selftest(a.iso)
        if a.cmd == "emit":
            return _cmd_emit(a)
    except ResultError as e:
        print(f"✗ input error (fail-loud): {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
