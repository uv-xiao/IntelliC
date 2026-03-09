# Layer 3 — Passes, Pipeline, and Solver

This layer describes how HTP transforms staged programs.

## Narrative

The current compiler is not a single hard-coded lowering script anymore. It has a registered pass surface, a registered pipeline surface, and a capability solver that checks backend and extension requirements before the pipeline runs.

The default implemented pass spine includes canonicalization, semantic modeling, type/layout/effect checks, schedule analysis/application, warp specialization analysis/application, software pipeline analysis/application, and package emission.

Extension participation is also real. MLIR CSE can participate as an extension-owned round-trip island. That still runs inside the same stage discipline: staged artifacts, pass trace, identity maps, and replay remain first-class.

## Visual model

```text
program
  -> solver preflight
  -> pass registry + pipeline template
  -> staged pass results
  -> package emission
```

```text
core passes ----+
                +--> pass manager --> ir/pass_trace.jsonl
extension passes+
```

## Implemented contracts

- backend capability facts come from backend declarations
- pass and pipeline templates are registry-visible
- `requires_satisfied` and state deltas are recorded in `ir/pass_trace.jsonl`
- MLIR round-trip participation is explicit extension behavior, not hidden backend magic

## Main code anchors

- `htp/solver.py`
- `htp/passes/manager.py`
- `htp/passes/trace.py`
- `htp/passes/registry.py`
- `htp/pipeline/defaults.py`
- `htp/pipeline/registry.py`
- `htp_ext/mlir_cse/`
