# Backend Depth Closure

- ID: `021-backend-depth-closure`
- Branch: `htp/feat-backend-depth-closure`
- PR: `#56`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Close the remaining backend-depth and extension-breadth gap in `docs/todo/backends_and_extensions.md`. This task broadens PTO beyond the current `a2a3sim`-anchored path, deepens NV-GPU runtime/profiling and Blackwell-specialized behavior, strengthens the AIE integration, and adds one additional extension backend only if it clearly reuses the shared compiler substrate.

## Why

- contract gap: `docs/todo/backends_and_extensions.md` still had partial and open items even though the shared architecture was already sound
- architectural reason: the remaining work should prove backend depth without introducing backend-local semantic forks
- user-facing reason: the same human-first frontends and staged artifacts should discharge into richer backend/runtime behavior

## Scope Checklist

- [x] broaden PTO target/package/runtime support beyond the current `a2a3sim` anchor
- [x] deepen NV-GPU lowering/runtime breadth, profiling, and Blackwell specialization
- [x] deepen the AIE path beyond the current reference integration
- [x] add one additional extension backend only if it strengthens the shared-substrate story
- [x] close `docs/todo/backends_and_extensions.md` and sync summary counts

## Code Surfaces

- PTO: `htp/backends/pto/`, `htp/bindings/pto.py`, `htp/bindings/pto_runtime_adapter.py`
- NV-GPU: `htp/backends/nvgpu/`, `htp/bindings/nvgpu.py`, `htp/bindings/nvgpu_cuda_adapter.py`
- AIE: `htp_ext/aie/`, `htp/bindings/aie.py`, `htp/bindings/aie_toolchain_adapter.py`
- CPU reference: `htp_ext/cpu_ref/`, `htp/bindings/cpu_ref.py`
- docs: `docs/design/backends_and_extensions.md`, `docs/todo/backends_and_extensions.md`, `docs/todo/README.md`

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the motivating gap
- [x] a human-friendly example update or addition
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete backend or artifact contract.

## Documentation Plan

- [x] update `docs/design/` for implemented behavior
- [x] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. add focused tests for the remaining backend-depth gaps
3. land PTO / NV-GPU / AIE / extension updates
4. sync examples and docs
5. rebase, review, and merge

## Review Notes

Reviewers should check that new backend depth still flows from the shared compiler substrate and emitted artifacts rather than introducing ad-hoc backend-only semantic state.
