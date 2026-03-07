# HTP Framework Completion Design

**Date:** 2026-03-07

## Goal

Define the next completion phase for HTP so the framework progresses in a disciplined order: first stabilize the user-facing compile and replay contract, then deepen backend execution realism, and only then strengthen the semantics of the core pass pipeline.

## Context

The repository already contains the core substrate for staged artifacts, pass contracts, replay/runtime behavior, bindings, PTO/NVGPU backends, and an MLIR CSE extension example. The remaining risk is no longer missing scaffolding. The risk is contract drift across three coupled layers:

1. user-facing compile/package/replay UX,
2. backend execution realism,
3. semantic depth of the core compiler passes.

If these are deepened out of order, the codebase will accumulate backend-specific compensations and the canonical Python-space contract will weaken.

## Ordering Decision

The next phase is explicitly ordered as:

1. **A — compile/package UX**
2. **C — backend execution realism**
3. **B — semantic pass deepening**

This ordering is intentional.

- `A` freezes the public compiler contract.
- `C` proves that contract can drive real backend-oriented behavior.
- `B` then deepens compiler meaning on top of stable package, replay, and binding rails.

## Scope A: Compile and Replay Contract

### Objective

Make `htp.compile_program(...)` the canonical entrypoint and ensure emitted stage packages are consistently replayable in `sim`.

### Required outcomes

- `htp.compile_program(...)` is the single user-facing entrypoint for end-to-end compilation.
- Target parsing is normalized into backend plus backend profile/option.
- Every stage emits a runnable `program.py` artifact representing the staged Python-space program snapshot.
- Pipeline-only packages can be replayed and validated even before a backend-specific package is emitted.
- Compile-time validation happens immediately; malformed packages are rejected at compile time, not discovered later in binding or replay.

### Architectural rule

`A` is about package and replay correctness, not about stronger compiler semantics. It must not introduce backend-specific logic into generic pass or artifact layers.

## Scope C: Backend Execution Realism

### Objective

Deepen PTO and NVGPU from artifact emitters into more realistic binding-owned execution surfaces without changing core ownership boundaries.

### Required outcomes

- PTO binding returns normalized structured results for `validate`, `build`, `load`, `run`, and `replay`.
- NVGPU binding does the same, with `.cu` preserved as the authoritative emitted source artifact.
- Derived outputs such as `.ptx` or compiled binaries remain secondary build outputs under `build/`.
- Validation checks parity between manifest-declared metadata and backend-emitted metadata surfaces.
- Toolchain absence and malformed package state produce explicit structured diagnostics, not implicit crashes.

### Architectural rule

Core owns orchestration and contracts; bindings own backend-specific behavior. No CUDA-specific or PTO-specific semantics should leak into generic runtime, pass, or artifact code.

## Scope B: Semantic Pass Deepening

### Objective

Make the default pass spine semantically meaningful while preserving Python-space as canonical and preserving replayability.

### Required outcomes

- `ast_canonicalize` performs explicit program normalization instead of pass-through behavior.
- `typecheck_layout_effects` records real typed/layout/effect analysis payloads.
- `analyze_schedule` emits meaningful schedule analysis instead of placeholder summaries.
- `apply_schedule` rewrites the staged program in ways that reflect the analysis.
- `emit_package` preserves the replayable staged program and all relevant analyses.

### Architectural rule

This phase does not introduce a new semantic owner or a large new IR. It deepens staged Python-space state, analyses, and transforms while keeping every stage replayable in `sim`.

## Non-goals for the next phase

- No native MLIR semantic ownership in core.
- No expansion into a general optimization framework.
- No backend-specific semantics in core pass implementations.
- No weakening of stage replayability or artifact contract precision.

## Acceptance criteria

The next phase is complete only when all of the following hold:

- `htp.compile_program(...)` is the documented and tested compile entrypoint.
- Default pipeline stages replay from emitted `program.py` artifacts.
- Replay works for generic stage packages and backend packages.
- PTO and NVGPU bindings expose structured result records for the main lifecycle actions.
- NVGPU keeps `.cu` as the canonical emitted source artifact.
- Default pipeline passes expose non-trivial analysis and transformation behavior while preserving replayability.
- `pytest` and `pre-commit run --all-files` pass on the resulting branch.
