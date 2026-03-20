# Alignment Review Sync

- ID: `027-alignment-review-sync`
- Branch: `htp/feat-alignment-review-sync`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Turn the current repository review into the repo's normal docs structure. The branch should add a design-side status/alignment report, reopen concrete TODOs that the review shows are still real, and clean stale documentation claims that currently imply the framework is more complete than it is.

## Why

- contract gap: current docs claim `docs/todo/` is empty and 100% complete, but the review identified real remaining gaps in programming surfaces, backend depth, and documentation alignment
- user-facing impact: readers cannot currently tell which parts of HTP are solid, which are narrow, and which are overclaimed
- architectural reason: HTP's docs are part of the product contract; stale completion claims weaken the framework story and future task selection

## Scope Checklist

- [ ] add a comprehensive implemented-state review under `docs/design/`
- [ ] reopen concrete TODO items under `docs/todo/` based on the review
- [ ] fix stale references in `README.md` and `docs/design/`

## Code Surfaces

- producer: `docs/design/`, `docs/story.md`, `README.md`
- validator/binding: `N/A`
- tests: docs/layout consistency only if needed
- docs: `docs/design/`, `docs/todo/`, `docs/in_progress/`, `README.md`

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
2. land design-side status report and stale-reference cleanup
3. reopen TODO tracking from the review
4. verify docs consistency
5. rebase, review, and merge

## Review Notes

Reviewers should inspect whether reopened TODOs are concrete and justified, and whether the new design-side review separates implemented facts from future work cleanly.
