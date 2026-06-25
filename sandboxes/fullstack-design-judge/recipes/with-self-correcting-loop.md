# Recipe — fullstack-design-judge AS the Judge/evals standard for /self-correcting-loop

> Re-runnable composition. The fullstack-design rubric is the **VERIFY criteria + Judge standard**; the
> self-correcting-loop kernel owns DECIDE. **Zero new engine** (no new engine) — this sandbox ships only
> a DR-distilled domain rubric; DECIDE is reused verbatim (`requires: [self-correcting-loop]`). report-only boundary:
> report-only — the judge never edits the design/code and never auto-accepts FINAL; the human admits the
> target artifact + rubric, the deterministic kernel decides FINAL, no_progress/exhausted → SURFACE to human.
> Sibling precedent: `sandboxes/arch-fitness/recipes/with-self-correcting-loop.md` (generic structural fitness);
> this one is the BFF / 前後端 / AI-Agent-async DOMAIN judge. They compose the SAME kernel and are complementary.

## The two-tier flow — 引導宏觀架構 → 微觀代碼

The DR concepts split into two tiers, and the recommended flow GUIDES from macro to micro:

1. **MACRO loop** — converge the **system architecture** first, against `fullstack-design.macro.rubric.json`
   (10 architecture criteria, all `kind:rubric`/semantic; judged against a DESIGN doc). FINAL = every
   architecture axis ≥ threshold (zero-trust boundary, contract-first SSOT, BFF topology, async decoupling,
   protocol choice, fan-out design …). Do NOT start code until the architecture is FINAL.
2. **MICRO loop** — then converge the **code implementation**, against `fullstack-design.micro.rubric.json`
   (11 code criteria; the 7 mechanically-checkable axes are `kind:runnable`/zero-LLM exit codes, the 4
   semantic ones are `kind:rubric`). FINAL = every code axis passes.
3. **COMBINED check** — `fullstack-design.rubric.json` (all 21) for a single-pass full-compliance audit.

`$R` = a rubric in this dir · `$LK` = `sandboxes/self-correcting-loop/src/loop_kernel.py` (the composed kernel)
· `$ST` = `sandboxes/fullstack-design-judge/src/scorecard_template.py`.

## The exact-match contract (avoid the #1 footgun)

`loop_kernel.decide` requires **`scorecard keys == rubric ids` EXACTLY** (missing OR extra both fail-loud).
Emit the full id skeleton first, then VERIFY fills every value — never hand-build the scorecard:

```
python3 $ST --rubric <$R> > scorecard.json      # keys == every rubric id, values = FILL placeholders
# VERIFY edits scorecard.json: runnable id → an exit code (int, 0=pass); rubric id → an int 1-10.
```

## One iteration (PLAN / DO / VERIFY / DECIDE)

```
# PLAN  — read last iteration's focus (the weakest axis) as this round's repair target:
python3 $LK state --loop <name> --state-dir sandboxes/fullstack-design-judge/state

# DO    — improve the design (macro loop) or the code (micro loop) toward that focus.
#         The judge NEVER edits the artifact — a human/agent does (report-only boundary).

# VERIFY — produce scorecard.json (keys from $ST):
#   • kind:runnable axes  → RUN the real check against the target code and record its EXIT CODE:
#       e.g. c_negative_value_rejected → run the bypass-UI negative-value test → 0 if 4xx-rejected
#            c_session_cookie_attrs    → parse Set-Cookie, assert HttpOnly+Secure+SameSite+__Host-+Path=/ → 0
#            c_atomic_concurrency      → run the N-parallel-request test → 0 if no double-spend
#            c_tests_pass              → run the test suite → its exit code
#     (a design-doc-only judge has no code to run → use the .macro. rubric, whose axes are all rubric.)
#   • kind:rubric axes    → the LLM honestly scores 1-10 against the criterion description (semantic).

# DECIDE (deterministic) — keys now match the rubric ids exactly:
python3 $LK decide --rubric <$R> --scorecard scorecard.json \
  --loop <name> --iso <ISO> --state-dir sandboxes/fullstack-design-judge/state; echo EXIT=$?
#   EXIT 0 = FINAL  (every criterion passes) → report verdict + per-criterion scores → done
#   EXIT 3 = ITERATING → read `focus` (weakest failing axis), go to PLAN (same --loop accumulates state +
#            no-progress/exhaustion guards; both SURFACE to human, never auto-continue)
#   EXIT 1 = bad input (scorecard/rubric malformed, e.g. a FILL placeholder left unfilled) → fix, do not fabricate
```

A failing `runnable` axis (exit ≠ 0) is a HARD blocker: it focuses BEFORE any low rubric score (effective
score 0), because a failing security/concurrency check matters more than a design reading two points low.

## Variants

- **Macro-only governance gate** — run just `.macro.` to decide whether an architecture proposal is ready,
  before any code exists. All axes are `kind:rubric`; FINAL = the design is architecturally sound.
- **Deterministic-only micro gate** — drop the 4 `kind:rubric` ids from `.micro.` and score only the 7
  runnable axes → a zero-LLM CI-style behavioral gate (negative-value reject, cookie attrs, atomic
  concurrency, idempotency, shared-schema, contract-test, tests-pass).

## Complementary loops (different axes — the human reconciles)

- **/arch-fitness** — generic structural fitness (Clean-Arch layering, Martin I/A/D coupling, AST smells).
  Orthogonal to this domain judge: run BOTH (arch-fitness for structure, fullstack-design-judge for
  BFF/async DOMAIN correctness). They compose the same self-correcting-loop kernel.
- **/refactor-loop** — per-function radon complexity, behavior-locked. Use it on a specific module after this
  judge focuses a `c_*` code axis there.
- **/improve-codebase-architecture** — deepening/consolidation candidates (SURFACED to human, never auto).

## report-only boundary
This judge only VERIFIES / supplies the Judge standard. `target + rubric admitted by human`; `FINAL decided by
the deterministic loop kernel`; `no_progress / exhausted → SURFACE to human`, never auto-continue, never auto-edit.
The per-criterion SCORING is still LLM/human VERIFY — the kernel makes the DECIDE aggregation honest and bounded,
it does not make a wrong score right (same honest residual as self-correcting-loop / arch-fitness).
