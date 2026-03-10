# Stronger Flagship Tests

- ID: `024-stronger-flagship-tests`
- Branch: `htp/feat-stronger-flagship-tests`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Strengthen the existing high-level test suites in place by replacing repeated toy vector-add and one-op matmul payloads with larger, human-written programs on the public HTP surfaces. The purpose is to make test coverage defend meaningful compiler behavior rather than only proving minimal plumbing.

## Why

- contract gap: many tests currently pass through weak programs that do not stress the surfaces they claim to cover
- user-facing impact: stronger tests will better defend the framework’s real programming model and examples
- architectural reason: if HTP claims human-first Python authoring, the test suite should exercise those authored programs directly rather than relying on small raw payload helpers

## Scope Checklist

- [ ] add shared richer authored programs for high-level test use
- [ ] replace toy programs in compiler, pipeline, and tools tests in place
- [ ] keep low-level raw-payload tests only where they are actually contract-directed
- [ ] sync programming-surface TODO/docs to reflect the stronger test baseline

## Code Surfaces

- test fixtures/helpers: `tests/`
- compiler/pipeline/tool suites: `tests/compiler/`, `tests/pipeline/`, `tests/tools/`
- docs: `docs/design/programming_surfaces.md`, `docs/todo/programming_surfaces.md`, `docs/todo/README.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating gap
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. The point is to make existing tests harder, not to inflate counts.

## Documentation Plan

- [ ] update `docs/design/` for the stronger test/program baseline if needed
- [ ] update `docs/todo/` to narrow the remaining programming-surface gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. add shared richer test programs
3. replace weak tests in place
4. sync docs
5. rebase, review, and merge

## Review Notes

Reviewers should check that replaced tests genuinely become stronger and more human-readable, rather than merely moving toy payloads into a shared helper.
