# Arknife Substrate Unification

- ID: `011-ark-unify-kernel`
- Branch: `htp/feat-ark-unify-kernel`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Refactor the Arknife integration so it reuses HTP's native kernel/value surface instead of maintaining a parallel tensor object model. Arknife-specific semantics should be represented as attached metadata over existing HTP buffers/values, plus explicit instruction/channel/hardware declarations that flow through the normal compiler pipeline. The result should make HTP more defensibly extensible and retargetable.

## Why

- contract gap: `htp.ark` currently defines its own `Tensor` type and trace-local object graph, which makes Arknife support look sidecar-like instead of substrate-reusing.
- user-facing impact: users see a separate mental model for Arknife programs instead of one coherent HTP surface with richer annotations.
- architectural reason: retargetability is stronger when frontend variants share one value model, one semantic state, and one lowering path.

## Scope Checklist

- [ ] remove the `htp.ark`-local tensor class from the public authoring path
- [ ] attach memory-space / axis-layout / Arknife metadata to HTP-native kernel args and values
- [ ] keep Arknife instruction/channel authoring but emit it over the shared value model
- [ ] preserve Ampere and Blackwell Arknife examples on the unified substrate
- [ ] update tests to defend the unification boundary explicitly
- [ ] update docs/design and docs/todo to explain the new reuse model

## Code Surfaces

- producer: `htp/kernel.py`, `htp/ark/__init__.py`, `examples/nvgpu_arknife_*`
- validator/binding: `htp/passes/program_model.py`, `htp/backends/nvgpu/`, `htp/bindings/nvgpu.py`
- tests: `tests/test_public_surfaces.py`, `tests/backends/nvgpu/`, `tests/examples/`
- docs: `docs/design/layers/02_programming_surfaces.md`, `docs/design/layers/05_backends_and_extensions.md`, `docs/todo/layers/02_programming_surfaces.md`, `docs/todo/layers/05_backends_and_extensions.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating gap
- [ ] human-friendly example updated or added
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land kernel/value substrate changes
3. land Arknife refactor on top of shared values
4. land examples and tests
5. sync docs
6. rebase, review, and merge

## Review Notes

Reviewers should inspect whether `htp.ark` still introduces hidden semantic ownership. The intended final state is: Arknife uses the same HTP value objects as other frontends, with additional metadata and instruction/channel declarations layered on top.
