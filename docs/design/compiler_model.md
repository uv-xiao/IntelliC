# Compiler Model, Semantics, and Typing

This document describes the implemented semantic center of HTP: what the compiler believes a program is, which facts are explicit, and where those facts live in code and artifacts.

## Why this topic exists

HTP is intentionally Python-AST-centric. That decision is not aesthetic. It exists to support three hard constraints at once:
- replayability of intermediate stages,
- extensibility without handing ownership to MLIR or a backend-local IR,
- and agent-friendly development with inspectable intermediate evidence.

The result is a dual representation strategy:
- Python-space remains the canonical program form,
- typed semantic state is owned by `ProgramModule`,
- and staged files expose that state through a compact `program.py` / `stage.json` / `state.json` contract.

This is the implemented answer to a common compiler failure mode: when semantic facts live only in pass-local memory, the compiler becomes difficult to debug, retarget, or evolve. HTP instead emits the important semantic state into artifacts so both humans and tools can inspect it.

## Visual model

```text
Python source / authoring surface
            |
            v
      ProgramModule
            |
            +--> program.py
            +--> state.json
            `--> stage.json
```

## Implemented semantic contracts

### Canonical form

The canonical compiler form today is:
- a staged Python program (`program.py`) that reconstructs `ProgramModule`,
- a machine-readable `state.json` export of that same semantic object graph,
- a typed execution path rooted at `ProgramModule.run(...)` and interpreter
  registration,
- and analysis artifacts referenced from `stage.json`.

The public frontend path now feeds that same owner directly. The implemented
`to_program_module()` path exists on:
- `htp.kernel.KernelSpec`
- `htp.routine.ProgramSpec`
- `htp.wsp.WSPProgramSpec`
- `htp.csp.CSPProgramSpec`

`htp.compile_program(...)` prefers that path over `to_program()`, so authored
surface objects can enter the pipeline without first collapsing back to a raw
program dict.

That ingress is now also registered rather than only inferred. Builtin public
surfaces are resolved through `htp.ir.frontends`, which gives the compiler an
explicit frontend-definition substrate for surface-to-`ProgramModule`
construction.

That substrate is now rule-backed in code:

- a rule-backed frontend-definition substrate now exists in
  `htp/ir/frontends/rules.py` (`FrontendRule`, `ProgramSurfaceRule`)
- builtin public surfaces are resolved through registered `FrontendSpec` objects
  in `htp/ir/frontends/__init__.py`, and compiler ingress routes through
  `FrontendSpec.build(...)` in `htp/compiler.py`
- builtin `htp.kernel`, `htp.routine`, `htp.wsp`, and `htp.csp` public
  surfaces now all use `rule=`-backed `FrontendSpec` registration
- `to_program_module()` on routine/WSP/CSP now delegates back through that
  registered frontend rule instead of owning a separate lowering path
- WSP and CSP public specs now carry typed top-level surface objects rather than
  raw dict payload fields before serialization into `state.json`
- remaining gap: those rules still rebuild nested stage/process-step structure
  from payload-shaped attrs rather than the final node-first
  rule/combinator frontend API

The current frontend set also records explicit dialect activation metadata into
`ProgramModule.meta`, so committed-stage state now carries both:
- the dependency-closed active dialect list
- and a manifest-style activation payload describing the requested dialects and
  resolved builtin dialect specs responsible for the authored program surface

That ingress path is now shared as well as direct. The public authoring
surfaces reuse the common frontend-definition substrate in `htp/ir/frontend.py`
to rebuild `KernelSpec`, assemble frontend workload/process structure, and
construct `ProgramModule` with consistent dialect metadata rather than each
surface hand-assembling its own module wrapper.

A stage is therefore not just “an AST snapshot”. It is a small evidence package describing both executable behavior and compiler understanding.

`ProgramModule` is now the semantic owner for committed stages. The normalized
`program.py` artifact rebuilds that typed object graph directly, and replay
executes the stage through `ProgramModule.run(...)` rather than treating staged
Python as a bag of payload constants.

The committed-stage core is now object-owned in two places that previously
leaked dict-first semantics:
- `items.kernel_ir` and `items.workload_ir` are typed semantic dataclasses
- `aspects.types`, `aspects.layout`, `aspects.effects`, and
  `aspects.schedule` are typed aspect wrappers
- `identity.entities`, `identity.bindings`, `identity.entity_map`, and
  `identity.binding_map` are typed identity wrappers
- `analyses.*` are typed analysis-record wrappers

The first typed-node substrate now also extends beyond a kernel-only proof
case. `htp.ir.core.nodes` and `htp.ir.interpreters.entrypoints` cover:
- kernel items
- task-graph items
- process-graph items

Those node families already execute through typed interpreter paths instead of
raw payload walkers, which is an important proof point for the AST-all-the-way
redesign.

### Staged state bundle

The current implementation emits and consumes a compact staged state bundle:
- `program.py`
- `state.json`
- `stage.json`

Inside `state.json`, the semantic model is still explicit:
- `items.kernel_ir`
- `items.workload_ir`
- `aspects.types`
- `aspects.layout`
- `aspects.effects`
- `aspects.schedule`
- `identity.*`

These are not decorative. Backends, replay tools, diagnostics, and semantic diffs all rely on them.

### Identity and mapping

HTP now treats identity as explicit compiler data rather than Python object identity:
- `node_id` for stage-local blame
- `entity_id` for semantic identity across stages
- `binding_id` for scoped variable/binding identity
- `state.json#/identity/entity_map` and `state.json#/identity/binding_map` for before/after provenance across non-trivial rewrites

This is part of the reason semantic diff and agent-oriented replay can work without heuristic AST matching.

### Type, layout, and effect substrate

The implemented substrate already covers:
- structured scalar dtypes including signed/unsigned integers, floating-point types, `bf16`, and `bool`
- `index`, symbolic dimensions, and staged shape payloads
- buffers, tensors, tiles, views, channels, and token-like value kinds
- alias validation for view/buffer relationships
- layout payloads using a facet-product structure
- explicit async-token, barrier, event, collective, and protocol obligations in `state.json#/aspects/effects`
- schedule payloads for mapping, specialization, pipelining, and launch structure
- a public `htp.types` surface that lets user code describe dtypes, symbolic
  dimensions, tensor shapes, distribution facts, and channel types without
  dropping into raw payload dictionaries

## Implemented feature inventory

### Value and storage model

The current code distinguishes:
- scalar values
- buffer-like objects
- tensor/tile-like semantic values
- views/aliases
- async tokens
- channels and protocol handles

This matters because the compiler is no longer relying on string encodings like `f32[MxK]` to describe semantic entities.

### Op semantics

The op registry in `htp/ir/core/op_specs.py` now provides explicit semantics for operations such as:
- richer unary and binary elementwise operators
- load/store
- cast
- broadcast
- reshape/view/transpose/slice/concat
- reduction
- async copy / wait
- barrier
- matrix-like operations
- explicit collectives including `allreduce`, `allgather`, and `reduce_scatter`
- channel/protocol-facing operations

The slice/view story is now stronger than a generic “view op exists” claim:
- native Python slicing on `KernelValue` lowers into explicit `slice` ops;
- loop-carried indices are preserved as symbolic index expressions instead of collapsing to ad-hoc strings;
- staged state carries both concrete replay offsets/sizes and human-readable `offset_exprs` / `size_exprs` so replay, codegen, and debugging all see the same tile/view intent.

That registry is the bridge between front-end authoring, legality checks, passes, and backend discharge.

### Compiler legality

The compiler already enforces real legality checks instead of only packaging whatever it was given:
- unsupported dtypes
- broken alias/view relationships
- mismatched layout or placement facts
- undischarged async/protocol obligations
- missing or redundant collective discharge
- illegal schedule directives for the current target/capabilities

### Serving-routine semantics

Serving routines are now first-class semantic objects instead of only example
conventions. When workload tasks carry serving attrs such as `phase`, `state`,
`stream`, and `batch`, `state.json#/items/workload_ir` emits a `routine` summary with:
- serving phases and the tasks in each phase
- state-transition edges derived from workload dependencies
- channel-flow summaries for serving streams

This is how HTP keeps serving semantics visible to replay, diagnostics, and
future passes instead of hiding them in Python helper code alone.

## Coding pointers

If you are working in this layer, start here:
- `htp/ir/core/aspects/` — typed aspect wrappers for committed-stage semantic state
- `htp/ir/core/semantics/` — core staged semantic dataclasses
- `htp/ir/program/module.py` — `ProgramModule`, entrypoints, and typed stage ownership
- `htp/ir/interpreters/registry.py` — interpreter registry for committed stage execution
- `htp/ir/program/render.py` — normalized staged Python rendering
- `htp/ir/core/types/` — structured type/value payloads
- `htp/ir/core/layout/` — layout helpers and payload structure
- `htp/ir/core/op_specs.py` — operation semantics and metadata
- `htp/types.py` — public structured dtype/shape/distribution/channel surface
- `htp/intrinsics.py` — intrinsic declarations and handler registration
- `htp/passes/program_model.py` — semantic synthesis from the current frontend/program surface
- `htp/passes/typecheck_layout_effects.py` — legality and typing checks
- `examples/pto_pypto_swiglu/demo.py` — a concrete fused unary/binary semantic proof case
- `examples/serving_routine/demo.py` — a serving-routine case with first-class
  typed channels, serving phases, and routine summary artifacts

Then inspect stage artifacts under `ir/stages/<id>/` from a compiled example to see what this layer actually emits.

## Current limits

The compiler-model topic is now closed at the stage-contract level. Remaining
future work lives mainly in frontend ergonomics, flagship example realism, and
backend depth rather than in a missing committed-stage semantic owner.
