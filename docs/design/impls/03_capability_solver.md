# Impl: Capability Solver

Current code anchors:

- solver model: `htp/solver.py`
- backend declarations: `htp/backends/pto/declarations.py`, `htp/backends/nvgpu/declarations.py`
- compiler preflight: `htp/compiler.py`
- template registry: `htp/pipeline/registry.py`
- pass registry: `htp/passes/registry.py`
- default pipeline execution: `htp/pipeline/defaults.py`
- solver tests: `tests/pipeline/test_solver.py`

Implemented behavior:

- the default pipeline is validated before pass execution
- template selection now comes from a registered template set and can choose
  between the plain default template and eligible extension-backed templates
- extension passes and extension-backed templates are discovered through
  `htp_ext/registry.py`, not hard-coded checks in the solver
- unsupported backend handlers fail early with `ir/solver_failure.json`
- missing pass capabilities and invalidated analyses fail through the same report
- layout/effect invariants participate in solver satisfiability through pass contracts
- final backend artifact requirements are checked after codegen emission
- MLIR CSE eligibility and template ids are solver-visible through extension
  results
- package resumption can rebuild solver-visible state from an emitted artifact package
- `ir/pass_trace.jsonl` records per-pass `requires_satisfied` details for capabilities, analyses, layout invariants, and effect invariants
- pipeline execution resolves selected pass ids through the registered pass
  surface, so extension-owned passes do not bypass the pass manager

Current scope:

- deterministic forward checking only
- a small registered template set with bounded OR-style template expansion
- extension-owned pass/template registration exists, but the registered set is
  still intentionally small
- backend-required outputs, supported-op facts, and target capability tags come from backend-owned declarations

This is an implemented surface, not roadmap material.
