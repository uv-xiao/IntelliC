# Impl: Capability Solver (pipeline satisfiability)

## Goal

Turn extension compatibility into a checkable constraint problem.

The solver is the mechanism that replaces:

- backend-specific `if/else` branching in pipelines, and
- implicit pass ordering “tribal knowledge”

with explicit capability/effect/layout constraints.

---

## 1) Inputs

- program capability set (from dialects, intrinsics, AST analysis)
- target backend requirements
- pipeline template:
  - ordered pass list, each with `requires/provides`
  - output artifact contract requirements
  - replay requirements (e.g. `artifact.runnable_py(sim)` for debug pipelines)

---

## 2) Outputs

- satisfiable pipeline instance (pass parameters bound)
- or a structured failure report:
  - missing capabilities
  - candidate providers (dialects/passes)
  - handler gaps (intrinsic without backend lowering)
  - undischarged effects / layout incompatibilities

---

## 3) Baseline algorithm (forward checking)

Start with a deterministic forward-checking solver:

1) compute initial capability state from:
   - enabled dialect packages,
   - imported intrinsic sets,
   - AST-derived requirements (effects/layout obligations),
   - target backend capability declarations.
2) walk pipeline passes in order:
   - verify `requires` is satisfied by current capability + invariants
   - apply `provides` and `invalidates` to capability state
3) verify final artifact contract requirements:
   - required `codegen/<backend>/...` outputs are produced by the selected packaging passes
   - required replay capabilities are satisfied (`RunnablePy` modes)

If any step fails, emit a failure report that points to *which* requirement failed and *why* (not “pass crashed”).

---

## 4) Failure report schema (recommended)

Emit a structured report (path recorded in the manifest), e.g. `ir/solver_failure.json`:

- `pipeline`: name/template id
- `failed_at_pass`: pass id (or `final_contract`)
- `missing_caps`: list of missing capability tags
- `missing_handlers`: intrinsic ids that lack `lower|emit|simulate` handlers for the target backend
- `layout_conflicts`: list of facet predicate conflicts with example node ids
- `undischarged_effects`: list of remaining obligations with example node ids
- `providers`: candidate passes/packages that could provide missing caps (if registered)
- `hints`: human-readable suggestions (optional, not relied on by tools)

This file is critical for agentic development: it is the “explainable unsat core”.

---

## 5) Design note: future extensions

Start with a simple forward-checking solver; later extensions may add:

- alternative pass choices (OR nodes)
- search-based optimization of pipeline
  - cost models (compile-time or runtime estimated)
  - “debug pipelines” that preserve `artifact.runnable_py(sim)` deeper into lowering
