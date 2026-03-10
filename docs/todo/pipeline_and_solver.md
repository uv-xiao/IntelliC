# TODO — Pipeline and Solver

This document tracks the remaining gap between the current registered pipeline discipline and the final extensibility/composition story.

## Completion snapshot

- total checklist items: 9
- complete: 6
- partial: 2
- open: 1

## Detailed checklist

### Solver capability and provider model
- [x] Use backend declarations instead of local hard-coded backend fact tables.
- [x] Make registered passes and pipeline templates solver-visible.
- [x] Make extension-provided passes/templates participate in solver-visible composition.
- [~] Broaden provider composition and package-resumption logic beyond the current implemented scope.
- [ ] Add richer search/cost selection beyond the current bounded deterministic choices.

### Pass and pipeline evidence
- [x] Emit `requires_satisfied` and state deltas into `ir/pass_trace.jsonl`.
- [x] Treat warp specialization and software pipelining as real staged analyses/transforms.
- [~] Broaden MLIR round-trip support beyond the current narrow extension slice.
- [x] Keep extension islands inside the same pass/artifact discipline.

## Why these tasks remain

The current system proves the architecture direction, but not the full search/composition space. The missing work is about more expressive pipeline selection and broader extension participation, not about inventing the first version of the solver.

## Coding pointers

Relevant anchors:
- `htp/solver.py`
- `htp/passes/manager.py`
- `htp/passes/registry.py`
- `htp/pipeline/defaults.py`
- `htp/pipeline/registry.py`
- `htp_ext/mlir_cse/`
