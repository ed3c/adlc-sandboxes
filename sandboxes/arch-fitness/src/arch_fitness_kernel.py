#!/usr/bin/env python3
"""arch_fitness_kernel — a deterministic architecture-fitness Judge/evals standard.

WHY (the demand,  human-admitted from a research report): a research
report argues the cure for "architecture erosion" / the "model-code gap" (模型-代碼縫隙) is NOT human review
but **architecture fitness functions** — design rules turned into executable tests that a CI gate runs to
mechanically reject any commit that violates the declared architecture (ArchUnit / PyTestArch / Spring
Modulith). This kernel COMPOSES that form: given a target source tree (the CODE) and an
arch-model spec (the MODEL), it measures the DR's machine-measurable concepts and renders a deterministic
verdict. The divergence between spec and code IS the model-code gap, made a machine fact.

WHAT IT MEASURES (the DR's complete concept space is enumerated by rubric(), honestly split into
deterministic / semantic / governance — this kernel owns only the DETERMINISTIC subset; semantic concepts
like APoSD deep-module quality are LLM-scored in the loop's VERIFY step, never faked here = anti
placebo-fitness):
  MACRO/strategic:  layer-dependency rule (Clean Arch) · module boundaries (modular monolith) ·
                    Martin I/A/D coupling + Zone-of-Pain (Distance from the Main Sequence)
  MICRO/tactical:   Long Method · Too Many Parameters · Large Class (AST-measurable code smells)

HOW IT COOPERATES WITH LOOP-ENGINEERING (the Judge/evals half): the report's per-dimension {value,
threshold, pass, kind} projects to a self-correcting-loop scorecard (`scorecard` CLI), so an existing loop
(/self-correcting-loop · /autoresearch · /loop) can DO (improve the codebase) → VERIFY (re-measure) →
DECIDE (loop kernel) without a new loop engine (no new engine). `focus` names the worst dimension =
the direction the next iteration should push, guiding both macro architecture and micro code.

DETERMINISM: pure function of (source tree, spec). No datetime.now()/random — the only timestamp source is
an explicit `iso` arg. All output lists are sorted; the verdict is a pure function of inputs (deterministic).

EXIT SEMANTICS (CLI):
  measure  : 0 = PASS (0 hard violations) · 2 = FAIL (layer/boundary erosion) · 1 = bad input
  selftest : 0 = kernel measures the bundled fixtures correctly · 1 = a self-check failed
  rubric   : 0 = printed the complete-concept Judge/evals standard
  scorecard: 0 = projected a report to a self-correcting-loop scorecard · 1 = bad input
  status   : 0 = printed a bounded latest-measurement snapshot (DCI source) · 1 = unreadable

Related docs:
- Interface contract: sandboxes/arch-fitness/SKILL.md (C1-C5) + manifest.yaml
- Absorbed form: the absorbed-form notes (withheld from this mirror)
- Loop cooperation: .claude/skills/skill-conformance-hub/modules/loop-cooperation-spec.md (L1-L6)
- Convention: sandboxes/README.md + sandboxes/_TEMPLATE/
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_THRESHOLDS = {
    "max_method_loc": 60,    # Long Method — generous default (DR cites 20; tune per target via spec)
    "max_params": 5,         # Too Many Parameters
    "max_class_methods": 20, # Large Class
    "max_distance": 0.5,     # Distance from the Main Sequence (Zone of Pain/Uselessness boundary)
}

# the deterministic dimensions this kernel measures — rubric()'s deterministic concepts map onto these.
DIMENSION_IDS = ["layer_dependency", "module_boundary", "coupling_distance",
                 "long_method", "too_many_params", "large_class"]
HARD_DIMS = ("layer_dependency", "module_boundary")   # erosion = the model-code gap → hard CI reject
# coupling I/A/D is a SURFACED diagnostic, not a binary gate: a concrete+stable utility leaf legitimately
# sits in the Zone of Pain (D→1) yet may be fine if it rarely changes (Martin). So it is reported (zone
# detail in `coupling`) but never drives the verdict OR the focus — only layer/boundary/smell do.
REPORT_DIMS = ("coupling_distance",)

_FIX = Path(__file__).resolve().parents[1] / "fixtures"


class SpecError(Exception):
    """Fail-loud arch-model spec defect. Never silently coerced."""


# ── spec ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ArchSpec:
    components: dict           # name -> package prefix
    layer_rules: list          # [{from, must_not_access}]
    allowed_dependencies: dict  # name -> [allowed names]
    thresholds: dict
    root: str = ""


def load_spec(obj) -> ArchSpec:
    """Accept a path/str (YAML) or a dict. Fail-loud on empty components or dangling references."""
    if isinstance(obj, (str, Path)):
        import yaml
        p = Path(obj)
        if not p.exists():
            raise SpecError(f"spec file not found: {p}")
        obj = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SpecError("spec must be a mapping (YAML dict)")
    components = obj.get("components") or {}
    if not isinstance(components, dict) or not components:
        raise SpecError("spec.components must be a non-empty {name: package_prefix} mapping")
    names = set(components)
    layer_rules = obj.get("layer_rules") or []
    for r in layer_rules:
        if not isinstance(r, dict) or "from" not in r or "must_not_access" not in r:
            raise SpecError(f"layer_rule must have 'from' and 'must_not_access': {r!r}")
        for k in ("from", "must_not_access"):
            if r[k] not in names:
                raise SpecError(f"layer_rule references undeclared component {r[k]!r}")
    allowed = obj.get("allowed_dependencies") or {}
    for src, deps in allowed.items():
        if src not in names:
            raise SpecError(f"allowed_dependencies key {src!r} is not a declared component")
        for d in deps:
            if d not in names:
                raise SpecError(f"allowed_dependencies[{src!r}] references undeclared component {d!r}")
    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds.update(obj.get("thresholds") or {})
    return ArchSpec(components=dict(components), layer_rules=list(layer_rules),
                    allowed_dependencies=dict(allowed), thresholds=thresholds,
                    root=str(obj.get("root", "")))


# ── source-tree extraction (AST, deterministic) ───────────────────────────────

def _module_path(file: Path, root: Path) -> str:
    rel = file.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _component_of(module: str, components: dict):
    best, best_len = None, -1
    for name, prefix in components.items():
        pfx = str(prefix)
        if module == pfx or module.startswith(pfx + "."):
            if len(pfx) > best_len:
                best, best_len = name, len(pfx)
    return best


def _imported_modules(file_module: str, node) -> list[str]:
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    # ImportFrom
    if node.level == 0:
        return [node.module] if node.module else []
    base_parts = file_module.split(".")
    base = base_parts[: max(0, len(base_parts) - node.level)]
    prefix = ".".join(base)
    mod = (prefix + "." + node.module) if (prefix and node.module) else (prefix or node.module or "")
    return [mod] if mod else []


def _is_abstract(cls: ast.ClassDef) -> bool:
    for b in cls.bases:
        nm = b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", None)
        if nm in ("ABC", "Protocol"):
            return True
    for kw in cls.keywords:
        v = kw.value
        nm = v.attr if isinstance(v, ast.Attribute) else getattr(v, "id", None)
        if kw.arg == "metaclass" and nm == "ABCMeta":
            return True
    for n in cls.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in n.decorator_list:
                dn = d.attr if isinstance(d, ast.Attribute) else getattr(d, "id", None)
                if dn == "abstractmethod":
                    return True
    return False


def _param_count(fn, is_method: bool) -> int:
    a = fn.args
    n = len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs)
    n += 1 if a.vararg else 0
    n += 1 if a.kwarg else 0
    if is_method and (a.posonlyargs or a.args):
        first = (a.posonlyargs or a.args)[0].arg
        if first in ("self", "cls"):
            n -= 1
    return n


@dataclass
class _FileFacts:
    component: str
    file: str
    edges: list          # (target_component, lineno)
    classes: list        # (name, lineno, n_methods, abstract)
    functions: list      # (name, lineno, loc, params, is_method)


def _analyze_file(file: Path, root: Path, spec: ArchSpec):
    module = _module_path(file, root)
    comp = _component_of(module, spec.components)
    if comp is None:
        return None
    tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    method_nodes = set()
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for m in methods:
                method_nodes.add(id(m))
            classes.append((node.name, node.lineno, len(methods), _is_abstract(node)))
    functions = []
    edges = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_method = id(node) in method_nodes
            loc = (node.end_lineno or node.lineno) - node.lineno + 1
            functions.append((node.name, node.lineno, loc, _param_count(node, is_method), is_method))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for mod in _imported_modules(module, node):
                tgt = _component_of(mod, spec.components)
                if tgt is not None and tgt != comp:
                    edges.append((tgt, node.lineno))
    return _FileFacts(component=comp, file=str(file.relative_to(root)),
                      edges=edges, classes=classes, functions=functions)


# ── report ────────────────────────────────────────────────────────────────────

@dataclass
class FitnessReport:
    verdict: str
    focus: str | None
    layer_violations: list
    boundary_violations: list
    coupling: dict
    long_methods: list
    too_many_params: list
    large_classes: list
    dimensions: dict
    unassigned_files: list

    def to_dict(self) -> dict:
        return {
            "schema": "arch-fitness-report/v1",
            "verdict": self.verdict, "focus": self.focus,
            "layer_violations": self.layer_violations,
            "boundary_violations": self.boundary_violations,
            "coupling": self.coupling,
            "long_methods": self.long_methods,
            "too_many_params": self.too_many_params,
            "large_classes": self.large_classes,
            "dimensions": self.dimensions,
            "unassigned_files": self.unassigned_files,
        }


def _zone(instability: float, abstractness: float, distance: float, max_distance: float) -> str:
    if distance <= max_distance:
        return "main_sequence"
    if abstractness < 0.5 and instability < 0.5:
        return "pain"            # stable + concrete: hard to change, hard to extend
    if abstractness >= 0.5 and instability >= 0.5:
        return "uselessness"     # instable + abstract: nobody uses it
    return "off_sequence"


def measure(target_root, spec: ArchSpec) -> FitnessReport:
    """Pure: walk the source tree, build the import graph, and measure every deterministic dimension."""
    root = Path(target_root)
    facts = []
    unassigned = []
    for file in sorted(root.rglob("*.py")):
        if any(part in ("__pycache__", ".git", "node_modules") or part.startswith(".")
               for part in file.relative_to(root).parts):
            continue
        f = _analyze_file(file, root, spec)
        if f is None:
            unassigned.append(str(file.relative_to(root)))
        else:
            facts.append(f)

    # import graph: distinct cross-component edges + per-edge occurrences (with anchors)
    occurrences = []   # (src, tgt, file, lineno)
    for f in facts:
        for tgt, lineno in f.edges:
            occurrences.append((f.component, tgt, f.file, lineno))
    distinct = {(s, t) for s, t, _, _ in occurrences}

    # Ca/Ce per component
    comps = list(spec.components)
    ce = {c: len({t for (s, t) in distinct if s == c}) for c in comps}
    ca = {c: len({s for (s, t) in distinct if t == c}) for c in comps}

    # Na/Nc per component
    nc = {c: 0 for c in comps}
    na = {c: 0 for c in comps}
    for f in facts:
        for _name, _ln, _nm, abstract in f.classes:
            nc[f.component] += 1
            if abstract:
                na[f.component] += 1

    coupling = {}
    md = spec.thresholds["max_distance"]
    for c in comps:
        denom = ca[c] + ce[c]
        instability = (ce[c] / denom) if denom else 0.0
        abstractness = (na[c] / nc[c]) if nc[c] else 0.0
        distance = abs(abstractness + instability - 1)
        coupling[c] = {
            "ca": ca[c], "ce": ce[c], "nc": nc[c], "na": na[c],
            "instability": round(instability, 6), "abstractness": round(abstractness, 6),
            "distance": round(distance, 6),
            "zone": _zone(instability, abstractness, distance, md),
        }

    # layer-dependency violations (Clean Arch)
    forbidden = {(r["from"], r["must_not_access"]) for r in spec.layer_rules}
    layer_violations = sorted(
        ({"from": s, "to": t, "file": fl, "lineno": ln}
         for (s, t, fl, ln) in occurrences if (s, t) in forbidden),
        key=lambda v: (v["from"], v["to"], v["file"], v["lineno"]))

    # module-boundary violations (modular monolith allowed-deps whitelist)
    boundary_violations = sorted(
        ({"component": s, "imports": t, "file": fl, "lineno": ln}
         for (s, t, fl, ln) in occurrences
         if s in spec.allowed_dependencies and t not in spec.allowed_dependencies[s]),
        key=lambda v: (v["component"], v["imports"], v["file"], v["lineno"]))

    # micro / tactical smells
    th = spec.thresholds
    long_methods, too_many_params, large_classes = [], [], []
    for f in facts:
        for name, ln, loc, params, _ in f.functions:
            if loc > th["max_method_loc"]:
                long_methods.append({"name": name, "file": f.file, "lineno": ln, "loc": loc})
            if params > th["max_params"]:
                too_many_params.append({"name": name, "file": f.file, "lineno": ln, "params": params})
        for name, ln, nmeth, _abstract in f.classes:
            if nmeth > th["max_class_methods"]:
                large_classes.append({"name": name, "file": f.file, "lineno": ln, "methods": nmeth})
    long_methods.sort(key=lambda x: (x["file"], x["lineno"]))
    too_many_params.sort(key=lambda x: (x["file"], x["lineno"]))
    large_classes.sort(key=lambda x: (x["file"], x["lineno"]))

    distance_violations = sum(1 for c in comps if coupling[c]["zone"] != "main_sequence")

    dim_values = {
        "layer_dependency": len(layer_violations),
        "module_boundary": len(boundary_violations),
        "coupling_distance": distance_violations,
        "long_method": len(long_methods),
        "too_many_params": len(too_many_params),
        "large_class": len(large_classes),
    }
    axis = {"layer_dependency": "macro", "module_boundary": "macro", "coupling_distance": "macro",
            "long_method": "micro", "too_many_params": "micro", "large_class": "micro"}
    dimensions = {
        d: {"value": dim_values[d], "threshold": 0, "pass": dim_values[d] == 0,
            "kind": "deterministic", "axis": axis[d], "hard": d in HARD_DIMS,
            "gate": d not in REPORT_DIMS}
        for d in DIMENSION_IDS
    }

    verdict = "FAIL" if any(not dimensions[d]["pass"] for d in HARD_DIMS) else "PASS"
    # focus = worst dimension to guide the next iteration: hard failures first (declared order), else the
    # worst-count failing SOFT-GATE smell. report-only dimensions (coupling) never drive focus.
    focus = None
    for d in HARD_DIMS:
        if not dimensions[d]["pass"]:
            focus = d
            break
    if focus is None:
        soft_failing = [d for d in DIMENSION_IDS
                        if d not in HARD_DIMS and d not in REPORT_DIMS and not dimensions[d]["pass"]]
        if soft_failing:
            focus = max(soft_failing, key=lambda d: (dim_values[d], -DIMENSION_IDS.index(d)))

    return FitnessReport(
        verdict=verdict, focus=focus,
        layer_violations=layer_violations, boundary_violations=boundary_violations,
        coupling=dict(sorted(coupling.items())),
        long_methods=long_methods, too_many_params=too_many_params, large_classes=large_classes,
        dimensions=dimensions, unassigned_files=sorted(unassigned))


# ── the complete-concept rubric standard (the Judge/evals standard) ───────────

def rubric() -> list[dict]:
    """The DR's COMPLETE concept space as a Judge/evals standard, honestly typed:
    deterministic (this kernel measures it) · semantic (LLM scores it in the loop's VERIFY) ·
    governance (migration-time, outside a static-fitness gate). Every deterministic concept names a
    real kernel dimension so the standard cannot drift from what the kernel actually computes."""
    return [
        # MACRO / strategic
        {"id": "bounded_context_isolation", "axis": "macro", "kind": "semantic",
         "dr_concept": "DDD 限界上下文 / 通用語言劃分業務邊界",
         "guidance": "are module boundaries aligned to bounded contexts with a ubiquitous language?"},
        {"id": "layer_dependency_rule", "axis": "macro", "kind": "deterministic",
         "dimension": "layer_dependency", "dr_concept": "Clean Architecture 依賴規則 (依賴指向內層, 禁跨層)"},
        {"id": "module_boundary", "axis": "macro", "kind": "deterministic",
         "dimension": "module_boundary", "dr_concept": "模組化單體 / Spring Modulith allowedDependencies 白名單"},
        {"id": "coupling_main_sequence", "axis": "macro", "kind": "deterministic",
         "dimension": "coupling_distance", "dr_concept": "Martin I/A/D 耦合指標 + 主序列偏離 (痛苦區)"},
        # MICRO / tactical
        {"id": "module_depth", "axis": "micro", "kind": "semantic",
         "dr_concept": "APoSD 深模組 vs 淺模組 (簡單介面封裝強大實現)",
         "guidance": "is the interface narrow relative to the implementation it hides?"},
        {"id": "long_method", "axis": "micro", "kind": "deterministic",
         "dimension": "long_method", "dr_concept": "過長函數 (Long Method) → 提煉函數"},
        {"id": "too_many_parameters", "axis": "micro", "kind": "deterministic",
         "dimension": "too_many_params", "dr_concept": "過多參數 → 引入參數對象 / 保持對象完整"},
        {"id": "large_class", "axis": "micro", "kind": "deterministic",
         "dimension": "large_class", "dr_concept": "過大類別 (違反 SRP) → 提煉類別"},
        {"id": "self_documenting_vs_comments", "axis": "micro", "kind": "semantic",
         "dr_concept": "Clean Code 自解釋 vs APoSD 註釋即設計第一工具",
         "guidance": "do comments capture the why / contract that names cannot?"},
        {"id": "define_errors_out_of_existence", "axis": "micro", "kind": "semantic",
         "dr_concept": "APoSD 將錯誤定義為不存在 (重界定語義消除防禦性校驗)",
         "guidance": "can an interface's semantics absorb the edge case instead of throwing?"},
        {"id": "fowler_smells_residual", "axis": "micro", "kind": "semantic",
         "dr_concept": "Feature Envy / Shotgun Surgery / Duplicated Code / Speculative Generality",
         "guidance": "the non-AST-trivial smells — judged, not counted (kernel counts the measurable subset)"},
        # GOVERNANCE / evolutionary
        {"id": "strangler_fig_new_root", "axis": "governance", "kind": "governance",
         "dr_concept": "絞殺者模式新根切入點 A/B/C (Greenfield / Read-Facade / Write-Interception)",
         "guidance": "migration-time strategy selection — outside a static-fitness gate"},
        {"id": "shadow_dual_write_reconciliation", "axis": "governance", "kind": "governance",
         "dr_concept": "影子雙寫 + SHA-256 確定性 ID 對賬 + 連續 N 週 0-mismatch 切流閘",
         "guidance": "maps to a migration-gate analogy; a migration harness, not a fitness function"},
        {"id": "modular_monolith_choice", "axis": "governance", "kind": "governance",
         "dr_concept": "單體模組化優先於過早微服務化 (邏輯邊界 ≠ 物理邊界)",
         "guidance": "an architecture-style decision, surfaced for the human"},
    ]


# ── persistence / CLI helpers ─────────────────────────────────────────────────

def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def scorecard_from_report(report: dict, dims: list | None = None) -> dict:
    """Project the deterministic dimensions to a self-correcting-loop 'runnable' scorecard
    ({criterion_id: exit_code}, 0=pass / 1=fail) so an existing loop can DECIDE over arch-fitness.
    `dims` restricts the projection to a subset (the loop rubric may gate only the actionable dims — e.g.
    drop the surfaced-not-gated coupling_distance) — loop_kernel requires scorecard keys == rubric ids
    EXACTLY, so the subset keeps the projection turnkey. Fail-loud on an unknown dim."""
    selected = list(DIMENSION_IDS) if dims is None else list(dims)
    bad = [d for d in selected if d not in DIMENSION_IDS]
    if bad:
        raise SpecError(f"unknown scorecard dim(s) {bad}; valid dims: {DIMENSION_IDS}")
    return {d: (0 if report["dimensions"][d]["pass"] else 1) for d in selected}


def _trace_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "trace"


def _render_status(report: dict, iso: str) -> str:
    dims = report["dimensions"]
    lines = [f"arch-fitness {iso} → verdict: {report['verdict']} · focus: {report.get('focus') or '— (all pass)'}"]
    lines.append("dimensions: " + ", ".join(f"{d}={dims[d]['value']}{'!' if not dims[d]['pass'] else ''}"
                                            for d in DIMENSION_IDS))
    pain = [c for c, v in report["coupling"].items() if v["zone"] == "pain"]
    if pain:
        lines.append("zone-of-pain components: " + ", ".join(sorted(pain)))
    if report.get("unassigned_files"):
        lines.append(f"unassigned files (outside model): {len(report['unassigned_files'])}")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cmd_measure(args) -> int:
    spec = load_spec(Path(args.spec))
    report = measure(Path(args.target), spec).to_dict()
    if args.report:
        _atomic_write_json(Path(args.report), report)
    else:
        _atomic_write_json(_trace_dir() / f"{args.iso}-measure.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == "PASS" else 2


def _cmd_rubric(_args) -> int:
    print(json.dumps(rubric(), ensure_ascii=False, indent=2))
    return 0


def _cmd_scorecard(args) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    dims = [d.strip() for d in args.dims.split(",") if d.strip()] if args.dims else None
    print(json.dumps(scorecard_from_report(report, dims), ensure_ascii=False, indent=2))
    return 0


def _cmd_status(args) -> int:
    traces = sorted(_trace_dir().glob("*-measure.json"))
    if not traces:
        print("[no measurement yet — run /arch-fitness measure --target <repo> --spec <model.yaml>]")
        return 0
    report = json.loads(traces[-1].read_text(encoding="utf-8"))
    print(_render_status(report, traces[-1].stem.replace("-measure", "")))
    return 0


def _cmd_selftest(iso: str) -> int:
    checks: list[tuple[str, bool]] = []

    sample = measure(_FIX / "sample_project", load_spec(_FIX / "sample_project.arch.yaml"))
    lv = {(v["from"], v["to"]) for v in sample.layer_violations}
    bv = {(v["component"], v["imports"]) for v in sample.boundary_violations}
    checks.append(("layer_violation_detected", ("controllers", "persistence") in lv))
    checks.append(("both_boundary_breaches", {("controllers", "persistence"),
                                              ("workflow", "controllers")} <= bv))
    checks.append(("long_method_detected", any(m["name"] == "place_order" for m in sample.long_methods)))
    checks.append(("too_many_params_detected", any(m["name"] == "place_order" and m["params"] == 6
                                                   for m in sample.too_many_params)))
    checks.append(("large_class_detected", any(c["name"] == "OrderRepo" for c in sample.large_classes)))
    checks.append(("persistence_zone_pain", sample.coupling["persistence"]["zone"] == "pain"))
    checks.append(("sample_verdict_fail", sample.verdict == "FAIL"))
    checks.append(("focus_is_hard_dim", sample.focus in HARD_DIMS))

    clean = measure(_FIX / "clean_project", load_spec(_FIX / "clean_project.arch.yaml"))
    # the discriminating reverse case: a conforming tree MUST verdict PASS — a kernel that flagged
    # everything (placebo) would fail here.
    checks.append(("clean_verdict_pass", clean.verdict == "PASS"))
    checks.append(("clean_focus_none", clean.focus is None))

    try:
        load_spec({"components": {}})
        checks.append(("spec_failloud", False))
    except SpecError:
        checks.append(("spec_failloud", True))

    rb = rubric()
    checks.append(("rubric_three_axes", {"macro", "micro", "governance"} <= {c["axis"] for c in rb}))
    checks.append(("rubric_det_dims_real", all(c.get("dimension") in DIMENSION_IDS
                                               for c in rb if c["kind"] == "deterministic")))

    ok = all(p for _, p in checks)
    trace = {"schema": "arch-fitness-selftest/v1", "iso": iso, "ok": ok,
             "checks": [{"name": n, "pass": p} for n, p in checks]}
    _atomic_write_json(_trace_dir() / f"{iso}-selftest.json", trace)
    print(f"# arch_fitness_kernel selftest {iso} → {'🟢' if ok else '🔴'}")
    for n, p in checks:
        print(f"  {'PASS' if p else 'FAIL'}  {n}")
    return 0 if ok else 1


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="arch_fitness_kernel",
                                 description="deterministic architecture-fitness Judge/evals standard (deterministic)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_m = sub.add_parser("measure", help="measure a target source tree against an arch-model spec")
    p_m.add_argument("--target", required=True, help="root of the source tree to measure (the CODE)")
    p_m.add_argument("--spec", required=True, help="arch-model YAML (the MODEL)")
    p_m.add_argument("--iso", required=True, help="deterministic timestamp (no datetime.now)")
    p_m.add_argument("--report", help="write the report JSON here (default: trace/<iso>-measure.json)")

    p_self = sub.add_parser("selftest", help="measure bundled fixtures, assert correctness (runtime_trace_cmd)")
    p_self.add_argument("--iso", required=True)

    sub.add_parser("rubric", help="print the complete-concept Judge/evals standard (macro/micro/governance)")

    p_sc = sub.add_parser("scorecard", help="project a report to a self-correcting-loop scorecard (loop cooperation)")
    p_sc.add_argument("--report", required=True)
    p_sc.add_argument("--dims", help="comma-separated subset of dimensions to project (default: all 6)")

    sub.add_parser("status", help="print a bounded latest-measurement snapshot (DCI injection source)")

    a = ap.parse_args(argv[1:])
    try:
        if a.cmd == "measure":
            return _cmd_measure(a)
        if a.cmd == "selftest":
            return _cmd_selftest(a.iso)
        if a.cmd == "rubric":
            return _cmd_rubric(a)
        if a.cmd == "scorecard":
            return _cmd_scorecard(a)
        if a.cmd == "status":
            return _cmd_status(a)
    except SpecError as e:
        print(f"✗ spec error (fail-loud): {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
