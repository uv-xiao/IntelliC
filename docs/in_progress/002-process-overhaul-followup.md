# Process Overhaul Follow-up Cleanup

- ID: `002-process-overhaul-followup`
- Branch: `htp/feat-process-overhaul-followup`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Remove the stale in-progress task left behind by the docs/process overhaul merge and sync the TODO summary so the new workflow is internally consistent on `htp/dev`.

## Why

- contract gap: `docs/in_progress/` must only contain active feature tasks
- user-facing impact: the merged branch leaves misleading active-task state in the docs tree
- architectural reason: the repo workflow should enforce the same lifecycle it documents

## Scope Checklist

- [ ] remove the stale `001-docs-process-overhaul.md` task file
- [ ] clear the active-task list in `docs/in_progress/README.md`
- [ ] sync `docs/todo/README.md` wording for the landed docs/process discipline
- [ ] verify and merge the cleanup PR

## Code Surfaces

- producer: `docs/in_progress/`, `docs/todo/README.md`
- validator/binding: none
- tests: none expected beyond repo verification
- docs: workflow docs only

## Test and Verification Plan

Required:
- [x] one happy-path test if automation changes
- [x] one malformed-input / contract-violation test if automation changes
- [x] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added
- [ ] `pixi run verify` or documented fallback

This branch is docs-only. No new contract automation is expected.

## Documentation Plan

- [x] update `docs/design/` for implemented behavior
- [x] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land docs cleanup
3. verify
4. rebase, review, and merge

## Review Notes

Confirm that `docs/in_progress/` is empty of stale tasks after the cleanup, and that the TODO summary no longer claims the workflow discipline itself is missing.
