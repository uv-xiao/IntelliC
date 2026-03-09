# TODO Layer 1 — Compiler Model, Semantics, and Typing

This layer tracks the remaining gap between the current semantic substrate and the final intended compiler model.

## Completion snapshot

- total checklist items: 10
- complete: 6
- partial: 2
- open: 2

## Detailed checklist

### Shared semantic breadth
- [x] Stage explicit `kernel_ir`, `workload_ir`, `types`, `layout`, `effects`, and `schedule` sidecars.
- [x] Use explicit identity and mapping artifacts instead of relying on Python object identity.
- [~] Broaden the shared operation set beyond the current implemented mix of unary/binary elementwise, view, reduction, async, protocol, and matrix-like operations.
- [ ] Make the user-facing type surface as rich and stable as the internal staged payload model.

### Type/layout/effect maturity
- [x] Support structured scalar dtypes, `index`, symbolic dimensions, and structured shape payloads.
- [x] Support buffers, tensors, views, channels, and token-like values in the semantic model.
- [x] Keep alias validation and basic legality checks explicit in the compiler.
- [~] Broaden collective/distribution semantics and their discharge rules across more targets.

### Workload/routine depth
- [x] Represent workload-level routines in staged semantic artifacts.
- [ ] Make richer serving-routine semantics first-class rather than mostly example-level.

## Why these tasks remain

The implemented substrate is already strong enough to drive real backends and
meaningful tools. Recent progress includes fused unary+binary elementwise
semantics exercised by the PTO SwiGLU example. What remains is not foundational
cleanup; it is breadth. HTP still needs a wider semantic envelope before the
top-level story in `docs/story.md` is fully realized.

## Coding pointers

Relevant current anchors:
- `htp/ir/semantics.py`
- `htp/ir/types.py`
- `htp/ir/layout.py`
- `htp/ir/op_specs.py`
- `htp/passes/program_model.py`
- `htp/passes/typecheck_layout_effects.py`
