# Passes and Artifacts

## Aspects vs analyses

The distinction is operational, not cosmetic.

- `aspects`
  - long-lived semantic/state objects
  - may affect execution, legality, lowering, or rendering
- `analyses`
  - derived facts
  - always invalidatable

## Dependency and invalidation protocol

Every aspect/analysis should declare:

- dependencies
- invalidation conditions
- whether it is mandatory for execution, validation, lowering, or optimization

Every pass should declare a change footprint, for example:

- rewrites expressions/statements/regions
- introduces/removes bindings
- changes control structure
- changes storage/view structure
- changes dialect/intrinsic usage
- changes layout/effect/schedule facts

Default invalidation is conservative:

- if preservation cannot be proven, invalidate

Pass traces should record:

- invalidated analyses
- preserved/revalidated/recomputed aspects
- preservation reasons

## Pass API

Input:

- one validated `ProgramModule`

Output:

- one pass result containing:
  - resulting `ProgramModule`
  - change summary
  - invalidation/preservation summary
  - rewrite maps
  - optional evidence artifacts
  - diagnostics

Passes may use transient internal forms, including foreign IRs, but those
forms may not cross a global stage boundary unless they satisfy the full global
stage contract.

## Stage commit rule

A pass may commit a new stage only when the result satisfies:

- valid typed object graph
- valid identity / binding / scope structure
- valid aspect/analysis state after invalidation and revalidation
- renderable into normalized HTP Python
- rebuildable from that Python
- executable through interpreter/runtime, or explicitly replay-stubbed with
  structured diagnostics

## Compact stage artifact layout

Default committed stage layout:

- `program.py`
  - primary human/LLM artifact
- `stage.json`
  - compact stage index
- `state.json`
  - compact machine-readable bundle
- `evidence/`
  - optional heavy supporting artifacts only when needed

`state.json` bundles:

- module structure
- identity state
- aspects
- analyses

`program.py` and `state.json` must represent the same stage semantics.

No stage commits unless:

- `program.py` renders/imports
- rebuilding from `program.py` yields an equivalent `ProgramModule`
- `state.json` matches that same module semantically
- declared replay/execution contract is satisfied
