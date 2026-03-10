# Replay Reference Closure

- ID: `019-replay-reference-closure`
- Branch: `htp/feat-replay-reference-closure`
- PR: `#54`
- Status: `in_review`
- Owner: `Codex`

## Goal

Close the remaining replay/reference breadth gap in `docs/todo/artifacts_replay_debug.md`. This task broadens runtime intrinsic simulation so public kernels and staged programs can execute through reference semantics instead of falling into unsupported-intrinsic stubs for common operations. The intended result is that explicit replay stubs remain only for genuinely external boundaries, not for HTP's normal portable and NV-GPU intrinsic set.

## Why

- contract gap: replay still relies on stub fallback for too many implemented intrinsic shapes.
- user-facing impact: stage replay should stay useful for more real kernels, not only simple elementwise cases.
- architectural reason: artifact-first and Python-space claims are weaker if canonical staged programs frequently degrade into stub diagnostics instead of executable reference behavior.

## Scope Checklist

- [x] add replay/reference semantics for the main portable intrinsic set used by current examples and tests
- [x] add runtime-aware protocol semantics for channel intrinsics and single-process collective fallback
- [x] add NV-GPU reference semantics for the implemented instruction-plan intrinsics where a reasonable Python-space meaning exists
- [x] update tests and docs to mark the replay/debug topic closed

## Code Surfaces

- producer: `htp/intrinsics.py`, `htp/runtime/core.py`
- validator/binding: replay diagnostics and sidecars remain under existing artifact contracts
- tests: `tests/ir/test_intrinsics.py`, `tests/runtime/test_intrinsic_dispatch.py`, adjacent replay/example tests
- docs: `docs/design/artifacts_replay_debug.md`, `docs/todo/artifacts_replay_debug.md`, `docs/todo/README.md`

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
2. land runtime / intrinsic simulation changes
3. land tests and any example adjustments
4. sync docs
5. rebase, review, and merge

## Review Notes

Reviewers should inspect whether runtime-aware channel simulation stays deterministic and whether new reference semantics preserve readable replay behavior instead of silently inventing backend-specific semantics.
