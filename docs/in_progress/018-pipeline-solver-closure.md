# Pipeline and Solver Closure

- ID: `018-pipeline-solver-closure`
- Branch: `htp/feat-pipeline-solver-closure`
- PR: `TBD`
- Status: `planned`
- Owner: `Codex`

## Goal

Close the remaining solver and MLIR-island gaps so pipeline selection is no longer only a bounded deterministic choice. This task adds richer template scoring and provider composition, makes package-resumption explicit as a solver-visible provider path, and broadens the MLIR round-trip slice beyond the current scalar-only subset. The result should remove the remaining open item in `docs/todo/pipeline_and_solver.md` and reduce the partial items in that topic to zero.

## Why

- contract gap: solver selection is still too shallow and the MLIR extension is narrower than the intended extension story.
- user-facing impact: users should get better pipeline choice, better resume behavior, and a broader MLIR round-trip path without hand-picking templates.
- architectural reason: retargetable composition depends on solver/provider declarations being expressive enough to represent competing backends and extension-owned alternatives.

## Scope Checklist

- [ ] add richer template scoring and ranking inputs to solver-visible declarations
- [ ] make existing-package / package-resume state solver-visible and reusable in pipeline selection
- [ ] broaden the MLIR CSE extension from scalar exprs to a larger canonical elementwise slice
- [ ] update tests, docs/design, and docs/todo to reflect the closure

## Code Surfaces

- producer: `htp/solver.py`, `htp/pipeline/registry.py`, `htp/pipeline/defaults.py`, `htp_ext/mlir_cse/`
- validator/binding: solver failure sidecars and extension artifacts emitted under `extensions/mlir_cse/` and `ir/stages/*/islands/*`
- tests: `tests/pipeline/test_solver.py`, `tests/extensions/test_mlir_cse.py`, adjacent pipeline tests
- docs: `docs/design/pipeline_and_solver.md`, `docs/design/backends_and_extensions.md`, `docs/todo/pipeline_and_solver.md`, `docs/todo/README.md`

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

Reviewers should inspect whether the new scoring/ranking rules stay deterministic and whether MLIR broadening still preserves the existing identity-map contracts.
