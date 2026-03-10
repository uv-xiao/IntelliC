# Flatten broad-topic docs

- ID: `016-docs-topic-files`
- Branch: `htp/feat-docs-topic-files`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Replace the numbered layer-style documents under `docs/design/` and `docs/todo/` with a smaller set of broad topic files. The new tree should keep the implemented-vs-todo split, remove the layer framing from filenames and headings, and preserve concrete code pointers. This PR is documentation/process work only.

## Why

- contract gap: the current docs still read like an intermediate layer dump rather than a stable broad-topic architecture description
- user-facing impact: readers have to map layer numbers back to actual topics, which adds friction and makes the tree feel more mechanical than useful
- architectural reason: the docs tree should match the repository workflow directly: broad implemented topics, broad todo topics, and feature-sized in-progress tasks

## Scope Checklist

- [ ] rename `docs/design/*.md` and `docs/todo/*.md` topic files away from numbered layer names
- [ ] rewrite headings, references, and guidance to remove layer framing
- [ ] update tests, README files, and policy text to the new docs shape
- [ ] verify the repo still passes with the new docs layout

## Code Surfaces

- producer: `docs/design/`, `docs/todo/`, `docs/in_progress/`, `README.md`, `AGENTS.md`
- validator/binding: `tests/test_docs_layout.py`, `.github/scripts/check_pr_policy.py`
- tests: docs layout and PR policy tests
- docs: docs tree itself

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
2. rename and rewrite the broad-topic docs
3. update policy/tests for the new docs shape
4. sync README and TODO summaries
5. rebase, review, and merge

## Review Notes

Reviewers should check the tree shape carefully. The main risk is leaving stale numbered references or breaking the PR policy/docs layout checks.
