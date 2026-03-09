# Layered Docs Rewrite

- ID: `003-docs-layered-rewrite`
- Branch: `htp/feat-docs-layered-rewrite`
- PR: `TBD`
- Status: `in_review`
- Owner: `Codex`

## Goal

Rewrite the repository documentation so `docs/design/` and `docs/todo/` are both genuinely organized by layers, not just renamed directories. The result must make the implemented-vs-todo split obvious, clean out leftover legacy document shapes, and turn `docs/story.md` into the top-level final framework narrative.

## Why

- contract gap: the current docs tree has the right top-level folder names but still preserves old document shapes and old narrative splits
- user-facing impact: readers cannot cleanly navigate implemented layers, todo layers, and the final framework story
- architectural reason: the repository workflow depends on docs acting as a precise state machine: final story, landed layers, remaining layers, active work

## Scope Checklist

- [x] define the target layered structure for `docs/design/` and `docs/todo/`
- [x] rewrite `docs/design/README.md` into an architecture-first index
- [x] rewrite `docs/design/` into layered, code-backed documents with narrative and visual description
- [x] rewrite `docs/todo/README.md` into a true checklist summary
- [x] rewrite `docs/todo/` into layered future-feature documents
- [x] rewrite `docs/story.md` as the top-level intended framework narrative
- [x] remove obsolete leftover docs shapes and stale duplication
- [x] update repo guidance if doc lifecycle rules change
- [x] verify tree shape and references

## Code Surfaces

- producer: `docs/`, `README.md`, `AGENTS.md`, `.agent/rules/*`
- validator/binding: docs-policy automation if needed
- tests: docs layout / policy tests if the new structure changes invariants
- docs: all normative repo docs

## Test and Verification Plan

Required:
- [x] one happy-path policy/layout test if automation changes
- [x] one malformed-input / contract-violation test if automation changes
- [x] one regression test for the doc-layout expectations if needed
- [x] human-readable docs structure verified
- [x] `pixi run verify` or documented fallback

## Documentation Plan

- [x] update `docs/design/` for the implemented layered structure
- [x] update `docs/todo/` for the remaining layered structure
- [x] update `docs/story.md`
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. define layered structure and move files
3. rewrite narrative/index docs
4. sync guidance and tests
5. rebase, review, and merge

## Review Notes

Reviewers should check that the new docs are genuinely organized by layers rather than preserving old coarse documents under new names, and that no stale duplicates remain across `design`, `todo`, and `story`.
