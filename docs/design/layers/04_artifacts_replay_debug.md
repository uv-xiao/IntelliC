# Layer 4 — Artifacts, Replay, and Debugging

This layer describes the package contract that makes HTP inspectable, replayable, and diagnosable.

## Why this layer exists

HTP is artifact-first. That phrase is easy to say and easy to water down. In the current implementation it has a concrete meaning:
- the compiler emits packages whose file layout matters,
- replay is a real execution surface over staged Python,
- backend execution is a separate binding-owned surface,
- and diagnostics, traces, maps, and sidecars are meant to be consumed by both humans and tools.

Without this layer, the rest of the framework would be much harder to verify or evolve.

## Visual model

```text
package/
  manifest.json
  ir/stages/*
  codegen/<backend>/*
  build/*
  logs/*
```

```text
replay(package) -> staged Python + sim runtime
run(package)    -> binding + backend adapter
```

## Implemented package contracts

### Manifest and stage graph

A compiled package contains:
- `manifest.json`
- staged IR under `ir/stages/`
- backend-owned sources under `codegen/<backend>/`
- build outputs under `build/`
- logs and adapter traces under `logs/`

The manifest and stage graph are validated; they are not free-form dumps.

### Replay

Replay executes `ir/stages/<id>/program.py` through the runtime surface. This is distinct from backend package execution. If a stage reaches a boundary without simulator/reference semantics, it fails through a structured replay diagnostic rather than becoming silently non-executable.

### Diagnostics and traces

The current implementation already has:
- structured replay diagnostics
- binding validation diagnostics
- adapter traces
- binding logs
- semantic diff evidence that includes stage sidecars, ids, maps, and pass traces
- a diagnostic catalog with family and exact-code lookup

### Tool surface

The tool layer already includes:
- `htp replay`
- `htp verify`
- `htp diff --semantic`
- `htp explain`
- `htp bisect`
- `htp minimize`
- `htp promote-plan`

## Rationale

This layer is central to the HTP claim that retargetability and agent-friendliness require explicit intermediate evidence. Replay, semantic sidecars, logs, traces, and fix-hint references are part of the framework contract, not only debugging conveniences.

## Coding pointers

Primary code and schemas:
- `htp/artifacts/manifest.py`
- `htp/artifacts/validate.py`
- `htp/runtime/core.py`
- `htp/runtime/errors.py`
- `htp/bindings/validate.py`
- `htp/tools.py`
- `htp/diagnostics.py`
- `htp/__main__.py`
- `htp/schemas.py`

Tests worth reading together with this layer:
- `tests/tools/`
- `tests/golden/`
- `tests/runtime/`
- `tests/bindings/`

## Current limits

The artifact and debugging layer is strong, but it is not the final surface. Broader validation/debug depth still lives in `docs/todo/layers/04_artifacts_replay_debug.md`.
