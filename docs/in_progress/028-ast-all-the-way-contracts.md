# AST-All-the-Way Contracts

- ID: `028-ast-all-the-way-contracts`
- Branch: `htp/feat-ast-all-the-way-contracts`
- PR: `TBD`
- Status: `planned`
- Owner: `Codex`

## Goal

Turn the newly stated project objective into real compiler contracts. This feature should formalize what it means for HTP to be human-friendly and LLM-friendly through AST all the way, then start the first implementation slice that threads that rule through the compiler model, pass contracts, artifact surfaces, and extension boundaries.

## Why

- contract gap: the repo now states AST all the way as the primary project rule, but the implementation contracts do not yet enforce or expose that requirement consistently
- user-facing impact: without a clear contract, stage artifacts may remain replayable while still drifting away from native Python readability and editability
- architectural reason: this is the first gap reopened by the design review and it should drive the next redesign wave rather than stay only in story prose

## Scope Checklist

- [ ] define the normative AST-all-the-way contract at global stage boundaries
- [ ] thread that contract through pass and extension-island surfaces
- [ ] add tests and example evidence for readable runnable stage artifacts after non-trivial rewrites

## Code Surfaces

- producer: `htp/passes/`, `htp/pipeline/`, `htp/artifacts/`, `htp_ext/mlir_cse/`
- validator/binding: `htp/tools.py`, replay/package verification surfaces as needed
- tests: pipeline, replay, docs/process consistency
- docs: `docs/design/`, `docs/todo/`, `docs/in_progress/`, `README.md` only if the contract wording needs refinement

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

1. create task file and clear stale prior task file
2. land AST-all-the-way contract surface changes
3. land tests and example evidence
4. sync docs and TODO narrowing
5. rebase, review, and merge

## Review Notes

Reviewers should focus on whether the implementation really sharpens the compiler contract rather than only rephrasing docs, and whether extension/MLIR boundaries still return to Python-owned global stage artifacts.
