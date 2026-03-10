# Pipeline and Solver

This document describes the implemented transformation discipline: how HTP chooses a pipeline, how passes are registered and validated, and how extension participation works without hiding behind backend-specific ad hoc logic.

## Why this topic exists

Retargetability claims are weak if the compiler is effectively “just run these hard-coded passes in this order”. HTP’s implemented answer is not a fully general solver yet, but it is also not just a hard-coded script anymore. The current code already has:
- backend declarations as capability sources,
- pass and pipeline registries,
- a solver preflight step,
- explicit pass contracts,
- pass-trace emission with solver/legality evidence,
- extension-owned pipeline participation,
- existing-package resume as a solver-visible candidate,
- and dynamic selection traces instead of only static template ordering.

## Visual model

```text
target + package intent + extensions
                |
                v
          solver preflight
                |
                v
   registered pipeline template + passes
                |
                v
        staged artifacts + pass trace
```

## Implemented pass spine

The default pass spine currently includes:
- `ast_canonicalize`
- `semantic_model`
- `typecheck_layout_effects`
- `analyze_schedule`
- `apply_schedule`
- `analyze_warp_specialization`
- `apply_warp_specialization`
- `analyze_software_pipeline`
- `apply_software_pipeline`
- `emit_package`

The important point is not only the pass names. It is that each pass now has a declared role in the artifact discipline and solver/legality flow.

## Implemented feature inventory

### Pass contracts and traces

The pass system now records:
- `requires_satisfied`
- evolving capability state
- state deltas across passes
- staged analysis payloads
- stage summaries and sidecars

This is why replay and semantic diff can reason about “what changed where” instead of only comparing end states.

That same pass discipline now also governs staged Python rendering. The
pipeline-owned `ir/stages/<id>/program.py` artifacts are emitted as readable
runnable Python modules with top-level bindings instead of only a dumped payload
literal. That matters because pass boundaries are where HTP claims Python-space
canonicality; the boundary artifact should therefore remain both executable and
inspectable.

### Extension participation

The solver and pipeline system can now see extension-provided passes and templates. MLIR CSE is the current concrete proof. It enters as an extension-owned round-trip path, yet still emits staged evidence and participates in the same pass-trace discipline.

### Resume and dynamic selection

The solver now considers more than a static template list. A matching existing package can participate as a `htp.resume.v1` candidate when the target, entry identity, requested extensions, and required outputs still match the current request.

Candidate ranking is also richer than “smallest declared template cost”. The implemented selection trace now combines:
- base template cost,
- pass-count cost,
- extension-count cost,
- output-count cost,
- resume bonus,
- and requested-extension bonus.

This keeps selection deterministic while making it reflect actual reuse and extension intent.

### Broader MLIR round-trip slice

The MLIR CSE extension now handles a broader scalar integer elementwise slice than the original `add`/`mul` proof:
- `add`
- `sub`
- `mul`
- `div`

That is still intentionally narrow, but it is no longer only a two-op toy path. The import/export/replay contracts now cover a more meaningful canonical scalar expression subset.

### Scheduling passes as real compiler work

Warp specialization and software pipelining are implemented as actual staged analyses/transforms rather than pure design prose. That matters because they show how HTP intends to encode non-trivial optimization logic: as explicit pass effects with emitted evidence.

## Rationale

The real architectural claim here is that HTP wants extensibility through explicit contracts, not pass folklore. The current implementation proves that direction on the full current topic boundary:
- capability facts are not only in the solver file
- passes and templates are registries, not hidden imports
- extension-owned logic does not get a private artifact model
- package resume participates in solver-visible selection instead of living as a disconnected helper
- MLIR round-trip participation now spans a broader canonical operator slice

## Coding pointers

Primary code paths:
- `htp/solver.py`
- `htp/passes/manager.py`
- `htp/passes/trace.py`
- `htp/passes/registry.py`
- `htp/pipeline/defaults.py`
- `htp/pipeline/registry.py`
- `htp_ext/mlir_cse/`

When working here, inspect `ir/pass_trace.jsonl` together with `ir/stages/*/analysis/` and the active backend declarations.

## Current limits

The standalone pipeline-and-solver topic is now closed at the current repository scale. Remaining future work lives in neighboring topics such as richer compiler semantics, backend depth, and stronger autonomous agent loops rather than in a separate solver-architecture gap.
