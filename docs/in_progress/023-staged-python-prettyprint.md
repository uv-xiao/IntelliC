# Staged Python Pretty Printing and Surface TODO Reopen

- ID: `023-staged-python-prettyprint`
- Branch: `htp/feat-staged-python-prettyprint`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Improve staged Python artifacts so `ir/stages/<id>/program.py` is pretty-printed as readable runnable Python instead of a single giant serialized payload assignment. Reopen the programming-surfaces TODO from the LittleKernel comparison and turn the extracted lessons into tracked, detailed remaining tasks.

## Why

- contract gap: staged Python is runnable today, but not human-friendly enough to debug or inspect
- user-facing impact: stage artifacts should help reading, replaying, and diagnosing compiler state
- architectural reason: HTP claims Python-space canonicality, so staged Python must be a real readable surface rather than a dumped payload blob

## Scope Checklist

- [ ] add readable staged Python rendering for stage programs
- [ ] preserve exact replay semantics for staged programs
- [ ] add focused tests for staged program readability and replay
- [ ] reopen `docs/todo/` with detailed programming-surface TODOs derived from the LittleKernel comparison
- [ ] sync design docs to describe the staged Python contract clearly

## Code Surfaces

- producer: `htp/passes/replay_program.py`, `htp/passes/program_model.py`
- validator/binding: replay contract tests under `tests/bindings/`
- tests: `tests/pipeline/`, `tests/bindings/`, `tests/test_docs_layout.py`
- docs: `docs/design/artifacts_replay_debug.md`, `docs/design/programming_surfaces.md`, `docs/design/littlekernel_ast_comparison.md`, `docs/todo/README.md`, `docs/todo/programming_surfaces.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating gap
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must protect a concrete staged-program or TODO-tracking contract.

## Documentation Plan

- [ ] update `docs/design/` for implemented staged Python behavior
- [ ] update `docs/todo/` to add the reopened programming-surface gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. add tests for readable staged Python output
3. implement the staged Python renderer
4. reopen and sync the programming-surfaces TODO
5. rebase, review, and merge

## Review Notes

Reviewers should check that readability improves without changing replay semantics, and that the reopened TODOs are concrete, broad-topic tasks rather than vague notes.
