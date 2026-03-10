# Programming Surface Conciseness Review

- ID: `026-programming-surface-conciseness-review`
- Branch: `htp/feat-programming-surface-conciseness-review`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Produce a critical PL/compiler-oriented review of HTP's current programming surfaces, with emphasis on human conciseness, semantic directness, and extension health. The output of this branch is not a surface implementation; it is a concrete review that turns syntax and ergonomics problems into follow-up feature tasks.

## Why

- contract gap: `docs/design/programming_surfaces.md` describes the current surface, but the repository still lacks a rigorous critique of where the syntax remains too indirect or semantically weak
- user-facing impact: if flagship examples still read like staged builder choreography instead of natural programs, HTP will fail its human-first claim even if the compiler substrate works
- architectural reason: frontend surface debt should be converted into explicit follow-up tasks before more syntax accretes on the wrong abstraction boundary

## Scope Checklist

- [ ] compare current HTP kernel / WSP / CSP authoring against `references/pypto/`, `references/triton-distributed-knowingnothing/python/little_kernel/`, and current `examples/`
- [ ] identify concrete conciseness and semantic-directness failures with critical commentary
- [ ] convert those criticisms into explicit follow-up tasks under `docs/in_progress/` / `docs/todo/` as appropriate

## Code Surfaces

- producer: `htp/kernel.py`, `htp/wsp/`, `htp/csp/`, `examples/`
- validator/binding: none for this review task
- tests: none for this review task unless policy/docs checks require them
- docs: `docs/design/programming_surfaces.md`, `docs/design/littlekernel_ast_comparison.md`, `docs/todo/programming_surfaces.md`, `docs/in_progress/README.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added
- [ ] `pixi run verify` or documented fallback

This is a review/documentation task. If no code contract changes land, record why implementation tests are not applicable and run docs/policy verification instead.

## Documentation Plan

- [ ] update `docs/design/` if the review sharpens the implemented story
- [ ] update `docs/todo/` with precise follow-up tasks
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. perform reference-backed review
3. translate findings into TODO / follow-up tasks
4. sync design and in-progress docs
5. rebase, review, and merge

## Review Notes

Reviewers should check whether the criticism is technically grounded in the code and references rather than aesthetic preference, and whether the resulting follow-up tasks are large enough to drive real PRs.
