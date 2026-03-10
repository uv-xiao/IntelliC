# <Task Title>

- ID: `<NNN-slug>`
- Branch: `htp/feat-<topic>`
- PR: `<url or TBD>`
- Status: `in_progress`
- Owner: `Codex`

## Goal

State the feature-level goal in 2-5 sentences. This must be large enough to justify a PR with multiple commits.

## Why

- contract gap:
- user-facing impact:
- architectural reason:

## Scope Checklist

- [ ] item 1
- [ ] item 2
- [ ] item 3

## Code Surfaces

- producer:
- validator/binding:
- tests:
- docs:

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
2. land contract / substrate changes
3. land tests and examples
4. sync docs
5. rebase, review, and merge

## Review Notes

List technical risks reviewers should inspect carefully.
