# TODO — Pipeline and Solver

This document tracks the remaining gap between the current registered pipeline discipline and the final extensibility/composition story.

## Completion snapshot

- total checklist items: 9
- complete: 9
- partial: 0
- open: 0

## Detailed checklist

### Solver capability and provider model
- [x] Use backend declarations instead of local hard-coded backend fact tables.
- [x] Make registered passes and pipeline templates solver-visible.
- [x] Make extension-provided passes/templates participate in solver-visible composition.
- [x] Broaden provider composition and package-resumption logic beyond the current implemented scope.
- [x] Add richer search/cost selection beyond the current bounded deterministic choices.

### Pass and pipeline evidence
- [x] Emit `requires_satisfied` and state deltas into `ir/pass_trace.jsonl`.
- [x] Treat warp specialization and software pipelining as real staged analyses/transforms.
- [x] Broaden MLIR round-trip support beyond the current narrow extension slice.
- [x] Keep extension islands inside the same pass/artifact discipline.

## Why this topic is now closed

The current repository now has a complete pipeline/solver story at its present scope:

- backend and extension providers are solver-visible,
- resume is a solver-visible candidate instead of only a helper,
- selection uses a richer deterministic scoring trace,
- and the MLIR extension participates with a broader round-trip slice.

Future work can still deepen semantics or backend breadth, but it no longer needs a separate unfinished “pipeline and solver architecture” topic.

## Coding pointers

Relevant anchors:
- `htp/solver.py`
- `htp/passes/manager.py`
- `htp/passes/registry.py`
- `htp/pipeline/defaults.py`
- `htp/pipeline/registry.py`
- `htp_ext/mlir_cse/`
