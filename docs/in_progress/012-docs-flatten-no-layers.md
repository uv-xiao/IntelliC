# Flatten docs design/todo trees

- ID: `012-docs-flatten-no-layers`
- Branch: `htp/feat-docs-flatten-no-layers`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Remove the `layers/` nesting under `docs/design/` and `docs/todo/` so those trees are directly organized by feature documents. Keep `docs/design/` as implemented behavior only, `docs/todo/` as remaining work only, and make the codebase, policy scripts, tests, and references point at the flattened paths.

## Why

- contract gap: the current docs tree adds an unnecessary level of nesting that leaks into diagnostics, policy checks, tests, and guidance
- user-facing impact: the docs structure is harder to navigate and contradicts the intended simplified documentation surface
- architectural reason: future PR flow depends on stable, simple doc paths because design/todo references are part of emitted diagnostics and policy enforcement

## Scope Checklist

- [ ] move `docs/design/layers/*.md` to `docs/design/*.md`
- [ ] move `docs/todo/layers/*.md` to `docs/todo/*.md`
- [ ] update repo guidance, policy scripts, diagnostics, tests, and code references to the flattened paths
- [ ] keep `docs/reference/`, `docs/research/`, `docs/in_progress/`, and `docs/story.md` unchanged except for path references
- [ ] verify docs layout and policy tests against the new structure

## Code Surfaces

- producer: `docs/design/`, `docs/todo/`, `README.md`, `AGENTS.md`
- validator/binding: `htp/diagnostics.py`, `htp/bindings/validate.py`, `htp/agent_policy.py`, `.github/scripts/check_pr_policy.py`
- tests: `tests/test_docs_layout.py`, `tests/test_pr_policy_script.py`, `tests/tools/test_tools.py`, `tests/runtime/test_stub_diagnostics.py`, `tests/compiler/test_compile_program.py`, `tests/bindings/test_replay.py`, `tests/golden/test_diagnostics.py`
- docs: `docs/design/README.md`, `docs/todo/README.md`, moved feature docs

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
2. move feature docs to flattened paths
3. sync code, policy, and tests to the new paths
4. verify and open PR
5. rebase, review, and merge

## Review Notes

Reviewers should inspect all path-based references carefully because doc paths are used by diagnostics, policy enforcement, and tests in addition to markdown navigation.
