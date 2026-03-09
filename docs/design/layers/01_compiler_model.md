# Layer 1 — Compiler Model, Semantics, and Typing

This layer describes the implemented semantic center of HTP: what the compiler believes a program is, which facts are explicit, and where those facts live in code and artifacts.

## Why this layer exists

HTP is intentionally Python-AST-centric. That decision is not aesthetic. It exists to support three hard constraints at once:
- replayability of intermediate stages,
- extensibility without handing ownership to MLIR or a backend-local IR,
- and agent-friendly development with inspectable intermediate evidence.

The result is a dual representation strategy:
- Python-space remains the canonical program form,
- typed semantic sidecars make compiler reasoning explicit and machine-checkable.

This is the implemented answer to a common compiler failure mode: when semantic facts live only in pass-local memory, the compiler becomes difficult to debug, retarget, or evolve. HTP instead emits the important semantic state into artifacts so both humans and tools can inspect it.

## Visual model

```text
Python source / authoring surface
            |
            v
   canonical Python stage program
            |
            +--> kernel_ir.json
            +--> workload_ir.json
            +--> types.json
            +--> layout.json
            +--> effects.json
            +--> schedule.json
            +--> ids/*.json, maps/*.json
```

## Implemented semantic contracts

### Canonical form

The canonical compiler form today is:
- a staged Python program (`program.py`), plus
- explicit semantic payloads and analysis sidecars.

A stage is therefore not just “an AST snapshot”. It is a small evidence package describing both executable behavior and compiler understanding.

### Semantic payloads

The current implementation emits and consumes these sidecars as first-class compiler state:
- `kernel_ir.json`
- `workload_ir.json`
- `types.json`
- `layout.json`
- `effects.json`
- `schedule.json`

These are not decorative. Backends, replay tools, diagnostics, and semantic diffs all rely on them.

### Identity and mapping

HTP now treats identity as explicit compiler data rather than Python object identity:
- `node_id` for stage-local blame
- `entity_id` for semantic identity across stages
- `binding_id` for scoped variable/binding identity
- `maps/*.json` for before/after provenance across non-trivial rewrites

This is part of the reason semantic diff and agent-oriented replay can work without heuristic AST matching.

### Type, layout, and effect substrate

The implemented substrate already covers:
- structured scalar dtypes including signed/unsigned integers, floating-point types, `bf16`, and `bool`
- `index`, symbolic dimensions, and staged shape payloads
- buffers, tensors, tiles, views, channels, and token-like value kinds
- alias validation for view/buffer relationships
- layout payloads using a facet-product structure
- explicit async-token, barrier, event, collective, and protocol obligations in `effects.json`
- schedule payloads for mapping, specialization, pipelining, and launch structure

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

The op registry in `htp/ir/op_specs.py` now provides explicit semantics for operations such as:
- load/store
- cast
- broadcast
- reshape/view/transpose
- reduction
- async copy / wait
- barrier
- matrix-like operations
- channel/protocol-facing operations

That registry is the bridge between front-end authoring, legality checks, passes, and backend discharge.

### Compiler legality

The compiler already enforces real legality checks instead of only packaging whatever it was given:
- unsupported dtypes
- broken alias/view relationships
- mismatched layout or placement facts
- undischarged async/protocol obligations
- illegal schedule directives for the current target/capabilities

## Coding pointers

If you are working in this layer, start here:
- `htp/ir/semantics.py` — core staged semantic dataclasses
- `htp/ir/types.py` — structured type/value payloads
- `htp/ir/layout.py` — layout helpers and payload structure
- `htp/ir/op_specs.py` — operation semantics and metadata
- `htp/intrinsics.py` — intrinsic declarations and handler registration
- `htp/passes/program_model.py` — semantic synthesis from the current frontend/program surface
- `htp/passes/typecheck_layout_effects.py` — legality and typing checks

Then inspect stage artifacts under `ir/stages/<id>/` from a compiled example to see what this layer actually emits.

## Current limits

What is implemented here is already meaningful, but it is not the final semantic envelope. The missing breadth now lives in `docs/todo/layers/01_compiler_model.md`.
