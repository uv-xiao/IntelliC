# Impl: Capability Solver

Current code anchors:

- solver model: `htp/solver.py`
- backend declarations: `htp/backends/pto/declarations.py`, `htp/backends/nvgpu/declarations.py`
- compiler preflight: `htp/compiler.py`
- default template source: `htp/pipeline/defaults.py`
- solver tests: `tests/pipeline/test_solver.py`

Implemented behavior:

- the default pipeline is validated before pass execution
- unsupported backend handlers fail early with `ir/solver_failure.json`
- missing pass capabilities and invalidated analyses fail through the same report
- final backend artifact requirements are checked after codegen emission
- MLIR CSE eligibility is solver-visible through extension results

Current scope:

- deterministic forward checking only
- one default pipeline template
- backend-required outputs, supported-op facts, and target capability tags come from backend-owned declarations

This is an implemented surface, not roadmap material.
