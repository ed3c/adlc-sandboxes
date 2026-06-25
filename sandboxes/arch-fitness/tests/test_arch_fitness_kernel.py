"""
arch_fitness_kernel behavior tests — the deterministic architecture-fitness Judge/evals standard.

The kernel is a PURE function of (target source tree, arch-model spec): no Ollama, no network, no
datetime.now(). It measures the DR's machine-measurable concepts — Clean-Architecture layer-dependency
rules, modular-monolith module boundaries, Martin's I/A/D coupling metrics, and the AST-measurable code
smells (Long Method / Too Many Parameters / Large Class) — and renders a deterministic PASS/FAIL verdict
plus a per-dimension focus that guides the next loop iteration. Tests exercise BEHAVIOR through the public
interface (load_spec / measure / FitnessReport / rubric), never implementation detail.

Related docs:
- Implementation: sandboxes/arch-fitness/src/arch_fitness_kernel.py
- Interface contract: sandboxes/arch-fitness/SKILL.md (C1-C5) + manifest.yaml
- Absorbed form: the absorbed-form notes (withheld from this mirror)
"""
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
_FIX = _ROOT / "fixtures"
sys.path.insert(0, str(_SRC))

import arch_fitness_kernel as afk  # noqa: E402


@pytest.fixture
def sample_report():
    spec = afk.load_spec(_FIX / "sample_project.arch.yaml")
    return afk.measure(_FIX / "sample_project", spec)


@pytest.fixture
def clean_report():
    spec = afk.load_spec(_FIX / "clean_project.arch.yaml")
    return afk.measure(_FIX / "clean_project", spec)


# ── macro / strategic: Clean-Architecture layer-dependency rule ───────────────

def test_detects_layer_violation(sample_report):
    pairs = {(v["from"], v["to"]) for v in sample_report.layer_violations}
    assert ("controllers", "persistence") in pairs


def test_clean_project_has_no_layer_violations(clean_report):
    assert clean_report.layer_violations == []


# ── macro / strategic: modular-monolith module-boundary whitelist ─────────────

def test_detects_both_boundary_breaches(sample_report):
    pairs = {(v["component"], v["imports"]) for v in sample_report.boundary_violations}
    assert ("controllers", "persistence") in pairs   # not in allowed [workflow, domain]
    assert ("workflow", "controllers") in pairs       # reverse dep, not in allowed [persistence, domain]


def test_boundary_violation_carries_source_anchor(sample_report):
    v = next(v for v in sample_report.boundary_violations if v["component"] == "workflow")
    assert v["file"].endswith("order_workflow.py")
    assert isinstance(v["lineno"], int) and v["lineno"] > 0


# ── macro / strategic: Martin I/A/D coupling metrics ─────────────────────────

def test_coupling_metrics_for_persistence(sample_report):
    p = sample_report.coupling["persistence"]
    assert p["ca"] == 2          # controllers + workflow import it
    assert p["ce"] == 1          # it imports domain
    assert p["instability"] == pytest.approx(1 / 3, abs=1e-6)
    assert p["abstractness"] == 0.0   # OrderRepo is concrete
    assert p["distance"] == pytest.approx(2 / 3, abs=1e-6)
    assert p["zone"] == "pain"   # distance > max_distance, stable+concrete


def test_domain_is_maximally_stable(sample_report):
    d = sample_report.coupling["domain"]
    assert d["ce"] == 0          # domain imports no other component
    assert d["instability"] == 0.0


# ── micro / tactical: AST-measurable code smells ─────────────────────────────

def test_detects_long_method(sample_report):
    names = {m["name"] for m in sample_report.long_methods}
    assert "place_order" in names


def test_detects_too_many_params(sample_report):
    flagged = {m["name"]: m["params"] for m in sample_report.too_many_params}
    assert flagged.get("place_order") == 6


def test_detects_large_class(sample_report):
    names = {c["name"] for c in sample_report.large_classes}
    assert "OrderRepo" in names


def test_clean_project_has_no_smells(clean_report):
    assert clean_report.long_methods == []
    assert clean_report.too_many_params == []
    assert clean_report.large_classes == []


# ── verdict + focus (the Judge half: hard gate + direction) ──────────────────

def test_sample_verdict_is_fail(sample_report):
    assert sample_report.verdict == "FAIL"


def test_clean_verdict_is_pass(clean_report):
    assert clean_report.verdict == "PASS"


def test_focus_points_at_a_hard_dimension(sample_report):
    # a failing layer or boundary rule is a hard blocker → focus must be one of them, not a soft smell
    assert sample_report.focus in ("layer_dependency", "module_boundary")


def test_clean_focus_is_none(clean_report):
    assert clean_report.focus is None


def test_dimensions_expose_kind_for_loop_rubric(sample_report):
    dims = sample_report.dimensions
    # every DR-measured dimension is present and carries pass + kind so a loop can gate per its rubric
    for dim in ("layer_dependency", "module_boundary", "coupling_distance",
                "long_method", "too_many_params", "large_class"):
        assert dim in dims
        assert dims[dim]["kind"] == "deterministic"
        assert isinstance(dims[dim]["pass"], bool)


# ── determinism (pure function; stable ordering) ─────────────────────────────

def test_measure_is_deterministic():
    spec = afk.load_spec(_FIX / "sample_project.arch.yaml")
    a = afk.measure(_FIX / "sample_project", spec).to_dict()
    b = afk.measure(_FIX / "sample_project", spec).to_dict()
    assert a == b


# ── fail-loud input defects (the issue, never silently coerced) ─────────────────

def test_load_spec_fail_loud_on_layer_rule_with_unknown_component():
    with pytest.raises(afk.SpecError):
        afk.load_spec({"components": {"a": "pkg.a"},
                       "layer_rules": [{"from": "a", "must_not_access": "ghost"}]})


def test_load_spec_fail_loud_on_empty_components():
    with pytest.raises(afk.SpecError):
        afk.load_spec({"components": {}})


# ── the complete-concept rubric standard (Judge/evals coverage) ──────────────

def test_rubric_covers_macro_micro_and_governance_axes():
    rb = afk.rubric()
    axes = {c["axis"] for c in rb}
    assert {"macro", "micro", "governance"} <= axes


def test_rubric_marks_semantic_concepts_not_deterministic():
    rb = afk.rubric()
    kinds = {c["kind"] for c in rb}
    # honest taxonomy: APoSD deep-module quality etc. are semantic (LLM-scored), not faked as deterministic
    assert "semantic" in kinds
    assert "deterministic" in kinds
    # every deterministic rubric concept names a kernel dimension that actually exists
    dim_ids = set(afk.DIMENSION_IDS)
    for c in rb:
        if c["kind"] == "deterministic":
            assert c["dimension"] in dim_ids


# ── CLI contract (runtime_trace_cmd + loop cooperation) ──────────────────────

def _run(*args):
    return subprocess.run([sys.executable, str(_SRC / "arch_fitness_kernel.py"), *args],
                          capture_output=True, text=True)


def test_cli_selftest_exit_zero():
    r = _run("selftest", "--iso", "2026-06-24")
    assert r.returncode == 0, r.stdout + r.stderr


def test_cli_measure_exits_two_on_fail():
    r = _run("measure", "--target", str(_FIX / "sample_project"),
             "--spec", str(_FIX / "sample_project.arch.yaml"), "--iso", "2026-06-24")
    assert r.returncode == 2   # hard violations → exit 2 (distinct from 0=PASS, 1=bad input)


def test_cli_measure_exits_zero_on_clean():
    r = _run("measure", "--target", str(_FIX / "clean_project"),
             "--spec", str(_FIX / "clean_project.arch.yaml"), "--iso", "2026-06-24")
    assert r.returncode == 0, r.stdout + r.stderr


# ── scorecard projection for loop cooperation (self-correcting-loop) ──────────

def test_scorecard_projects_all_dims_to_exit_codes(sample_report):
    sc = afk.scorecard_from_report(sample_report.to_dict())
    assert set(sc) == set(afk.DIMENSION_IDS)
    assert sc["layer_dependency"] == 1   # failing dim → exit 1
    assert all(v in (0, 1) for v in sc.values())


def test_scorecard_dims_filter_keeps_only_requested(sample_report):
    # the loop rubric may gate only the actionable dims (not surfaced coupling); the projection must then
    # emit EXACTLY those keys so loop_kernel's keys-must-match-rubric contract holds with zero surgery.
    sc = afk.scorecard_from_report(sample_report.to_dict(), dims=["layer_dependency", "module_boundary"])
    assert set(sc) == {"layer_dependency", "module_boundary"}


def test_scorecard_dims_fail_loud_on_unknown_dim(sample_report):
    with pytest.raises(afk.SpecError):
        afk.scorecard_from_report(sample_report.to_dict(), dims=["layer_dependency", "ghost_dim"])


def test_cli_scorecard_dims_flag(sample_report, tmp_path):
    rep = tmp_path / "r.json"
    rep.write_text(__import__("json").dumps(sample_report.to_dict()), encoding="utf-8")
    r = _run("scorecard", "--report", str(rep), "--dims", "layer_dependency,large_class")
    assert r.returncode == 0, r.stdout + r.stderr
    sc = __import__("json").loads(r.stdout)
    assert set(sc) == {"layer_dependency", "large_class"}
