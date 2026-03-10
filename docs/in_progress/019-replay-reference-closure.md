# Replay Reference Closure

- ID: `019-replay-reference-closure`
- Branch: `htp/feat-replay-reference-closure`
- PR: `TBD`
- Status: `planned`
- Owner: `Codex`

## Goal

Close the remaining replay/reference breadth gap in `docs/todo/artifacts_replay_debug.md`. This task broadens runtime intrinsic simulation so public kernels and staged programs can execute through reference semantics instead of falling into unsupported-intrinsic stubs for common operations. The intended result is that explicit replay stubs remain only for genuinely external boundaries, not for HTP's normal portable and NV-GPU intrinsic set.

## Why

- contract gap: replay still relies on stub fallback for too many implemented intrinsic shapes.
- user-facing impact: stage replay should stay useful for more real kernels, not only simple elementwise cases.
- architectural reason: artifact-first and Python-space claims are weaker if canonical staged programs frequently degrade into stub diagnostics instead of executable reference behavior.

## Scope Checklist

- [ ] add replay/reference semantics for the main portable intrinsic set used by current examples and tests
- [ ] add runtime-aware protocol semantics for channel intrinsics and single-process collective fallback
- [ ] add NV-GPU reference semantics for the implemented instruction-plan intrinsics where a reasonable Python-space meaning exists
- [ ] update tests and docs to mark the replay/debug topic closed

## Code Surfaces

- producer: `htp/intrinsics.py`, `htp/runtime/core.py`
- validator/binding: replay diagnostics and sidecars remain under existing artifact contracts
- tests: `tests/ir/test_intrinsics.py`, `tests/runtime/test_intrinsic_dispatch.py`, adjacent replay/example tests
- docs: `docs/design/artifacts_replay_debug.md`, `docs/todo/artifacts_replay_debug.md`, `docs/todo/README.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating bug or gap
- [ ] human-friendly example updated or added
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land runtime / intrinsic simulation changes
3. land tests and any example adjustments
4. sync docs
5. rebase, review, and merge

## Review Notes

Reviewers should inspect whether runtime-aware channel simulation stays deterministic and whether new reference semantics preserve readable replay behavior instead of silently inventing backend-specific semantics.
