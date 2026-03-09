# Layer 1 — Compiler Model, Semantics, and Typing

This layer defines the implemented semantic center of HTP.

## Narrative

HTP keeps Python-space as the canonical compiler form. Compilation does not switch into an opaque internal IR that becomes the semantic owner. Instead, each stage emits runnable Python plus explicit semantic sidecars. The current implementation already stages:
- `kernel_ir.json`
- `workload_ir.json`
- `types.json`
- `layout.json`
- `effects.json`
- `schedule.json`
- identity and mapping files under `ids/` and `maps/`

This means the compiler model is dual:
- Python AST remains the canonical program representation
- typed semantic payloads make compiler reasoning explicit and machine-checkable

The implemented type/layout/effect substrate already covers scalar dtypes, `index`, symbolic dimensions, buffers, tensors, views, channels, tokens, layout facets, alias validation, async/barrier obligations, and protocol obligations.

## Visual model

```text
Python program
    |
    +-- runnable stage program.py
    +-- kernel_ir.json
    +-- workload_ir.json
    +-- types/layout/effects/schedule
    +-- ids/*.json and maps/*.json
```

## Implemented contracts

- stage programs remain replayable in `sim` or fail with a structured replay diagnostic
- semantic facts are emitted as artifacts, not hidden in pass-local memory only
- analyses that need cross-stage stability attach to `entity_id` / `binding_id`, not raw Python object identity
- legality failures surface through structured compiler diagnostics

## Main code anchors

- `htp/ir/semantics.py`
- `htp/ir/types.py`
- `htp/ir/layout.py`
- `htp/ir/op_specs.py`
- `htp/intrinsics.py`
- `htp/passes/program_model.py`
- `htp/passes/typecheck_layout_effects.py`
