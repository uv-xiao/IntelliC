# Docs and Process Overhaul

- ID: `001-docs-process-overhaul`
- Branch: `htp/feat-doc-process-overhaul`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Reorganize `docs/` into a stable implemented-vs-todo-vs-in-progress structure, add a mandatory in-progress task workflow for feature branches, and tighten agent guidance for documentation, examples, tests, and code readability. The result should make the repo easier to control, easier to review, and harder to drift.

## Why

- contract gap: the current docs split does not expose a strict TODO and in-progress workflow
- user-facing impact: contributors cannot reliably tell what is landed, planned, or currently being built
- architectural reason: the repo needs documentation and process to match the staged, contract-first development model

## Scope Checklist

- [ ] move implemented docs under `docs/design/`
- [ ] move unimplemented docs under `docs/todo/`
- [ ] add top-level `docs/story.md`
- [ ] add `docs/in_progress/` workflow and template
- [ ] remove obsolete docs directories
- [ ] update repo and agent guidance for the new process
- [ ] update example/test/documentation quality rules
- [ ] rewrite `README.md`

## Code Surfaces

- producer: `docs/`, `README.md`
- validator/binding: `.github/scripts/check_pr_policy.py` if needed
- tests: process-policy tests if path rules change
- docs: `AGENTS.md`, `.agent/rules/*`

## Test and Verification Plan

Required:
- [ ] one happy-path policy test if automation changes
- [ ] one malformed-input / contract-violation test if automation changes
- [ ] one regression test for changed PR-policy path rules if needed
- [ ] human-friendly example guidance updated
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land docs tree changes
3. land guidance and automation changes
4. sync README and remaining docs
5. rebase, review, and merge

## Review Notes

Review the final docs tree shape, path references, and PR/task workflow carefully. The risk is stale references or a process rule that the automation does not actually enforce.
