# Arknife Technique Integration

- ID: `010-arknife-integration`
- Branch: `htp/feat-arknife-integration`
- PR: `https://github.com/uv-xiao/htp/pull/45`
- Status: `in_review`
- Owner: `Codex`

## Goal

Integrate the core Arknife technique classes into HTP’s native programming and compiler stack: explicit hardware hierarchy, memory spaces, channels, instruction declarations, and an Arknife-style authoring surface that lowers into the existing HTP pipeline. The result should be real HTP functionality rather than a sidecar shim: examples, replay, lowering metadata, and NV-GPU codegen all need to recognize the new substrate. The implementation target is feature-class coverage across Ampere and Blackwell, anchored in reference-backed examples.

## Why

- contract gap: HTP currently has NV-GPU execution and WSP/CSP surfaces, but it does not expose a first-class explicit hardware/instruction model comparable to Arknife.
- user-facing impact: users cannot currently author HTP programs in the concise explicit-hierarchy style shown by Arknife’s CUDA examples, nor inspect profile-specific instruction/channel plans through HTP artifacts.
- architectural reason: explicit hardware, memory, and instruction declarations are the missing bridge between Python-native authoring and backend-specific scheduling/codegen depth.

## Scope Checklist

- [x] add a core hardware-model substrate for hierarchical parallel levels and memory spaces
- [x] add instruction and channel declarations that integrate with HTP intrinsics and semantic state
- [x] add an Arknife-style Python authoring surface that lowers into canonical HTP programs
- [x] thread hardware/instruction/channel facts through semantic analysis and stage artifacts
- [x] deepen NV-GPU lowering and emitted metadata for Ampere and Blackwell profile-specific Arknife-style programs
- [x] add reference-backed Ampere and Blackwell examples with local README docs
- [x] update design and todo docs to reflect implemented Arknife support

## Code Surfaces

- producer: `htp/ark/`, `htp/kernel.py`, `htp/wsp/__init__.py`, `examples/`
- validator/binding: `htp/backends/nvgpu/`, `htp/bindings/nvgpu.py`, `htp/bindings/nvgpu_cuda_adapter.py`
- tests: `tests/test_public_surfaces.py`, `tests/backends/nvgpu/`, `tests/examples/`, `tests/passes/`
- docs: `docs/design/layers/02_programming_surfaces.md`, `docs/design/layers/05_backends_and_extensions.md`, `docs/todo/layers/02_programming_surfaces.md`, `docs/todo/layers/05_backends_and_extensions.md`

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added
- [x] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [x] update `docs/design/` for implemented behavior
- [x] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land core hardware / instruction / channel substrate
3. land authoring surface and NV-GPU lowering changes
4. land examples and tests
5. sync docs
6. rebase, review, and merge

## Review Notes

Reviewers should check that this does not fork HTP into a parallel compiler path. The new Arknife-inspired surface must lower into the same canonical program model, replay contract, and NV-GPU backend selection used elsewhere. Ampere and Blackwell should remain two profiles of the same backend, with profile-specific instruction/channel facts represented explicitly instead of hidden string branching.
