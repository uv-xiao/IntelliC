# TODO — Compiler Model, Semantics, and Typing

This document tracks the remaining gap between the current semantic substrate and the final intended compiler model.

## Completion snapshot

- total checklist items: 10
- complete: 10
- partial: 0
- open: 0

## Detailed checklist

### Shared semantic breadth
- [x] Stage explicit `kernel_ir`, `workload_ir`, `types`, `layout`, `effects`, and `schedule` sidecars.
- [x] Use explicit identity and mapping artifacts instead of relying on Python object identity.
- [x] Broaden the shared operation set beyond the current implemented mix of unary/binary elementwise, view, reduction, async, protocol, and matrix-like operations.
- [x] Make the user-facing type surface as rich and stable as the internal staged payload model.

### Type/layout/effect maturity
- [x] Support structured scalar dtypes, `index`, symbolic dimensions, and structured shape payloads.
- [x] Support buffers, tensors, views, channels, and token-like values in the semantic model.
- [x] Keep alias validation and basic legality checks explicit in the compiler.
- [x] Broaden collective/distribution semantics and their discharge rules across more targets.

### Workload/routine depth
- [x] Represent workload-level routines in staged semantic artifacts.
- [x] Make richer serving-routine semantics first-class rather than mostly example-level.

## Why this topic is now closed

The semantic substrate now covers the missing breadth that previously kept this
topic open:
- the shared op set includes slice/concat plus explicit collectives beyond the
  earlier fused-elementwise core
- the public type surface has structured dtype, dim, shape, distribution, and
  channel helpers in `htp.types`
- collective/distribution discharge is explicit for `allreduce`, `allgather`,
  and `reduce_scatter`
- serving routines emit first-class routine summaries instead of relying on
  example-local conventions

## Coding pointers

Relevant current anchors:
- `htp/ir/semantics.py`
- `htp/ir/types.py`
- `htp/ir/layout.py`
- `htp/ir/op_specs.py`
- `htp/types.py`
- `htp/passes/program_model.py`
- `htp/passes/typecheck_layout_effects.py`
