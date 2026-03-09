# Restart WSP/CSP surfaces and flagship examples

- ID: `013-wsp-csp-surface-restart`
- Branch: `htp/feat-wsp-csp-surface-restart`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Replace the remaining dict-assembly feel in `htp.wsp` and `htp.csp` with decorator/builder-based authoring that reads like native Python. Rewrite the flagship WSP/CSP examples on top of that surface so they demonstrate non-trivial scheduling and protocol structure rather than collapsing to `store(C, A @ B)` plus a thin wrapper.

## Why

- contract gap: current WSP/CSP helpers are still mostly dict constructors, so the surface does not yet prove the intended HTP programming model
- user-facing impact: the examples remain too mechanical and undersell schedule/dataflow semantics
- architectural reason: if WSP/CSP stay thin dict wrappers, HTP still looks like a payload assembler instead of a compiler with coherent Python-native frontends

## Scope Checklist

- [x] add decorator/builder-based WSP authoring on top of the existing contract surface
- [x] add decorator/builder-based CSP authoring on top of the existing contract surface
- [x] keep backward compatibility for the current helper functions unless a stronger contract change is necessary
- [x] rewrite flagship WSP/CSP examples to use the new surface and richer kernel/protocol structure
- [x] update tests to defend the new public surface and the improved examples
- [x] sync `docs/design/` and `docs/todo/` after the surface/example upgrade

## Code Surfaces

- producer: `htp/wsp/__init__.py`, `htp/csp/__init__.py`, example demos under `examples/`
- validator/binding: `htp/compiler.py`, `htp/passes/program_model.py` if the surface needs additional lowering support
- tests: `tests/test_public_surfaces.py`, `tests/examples/test_examples.py`, any focused WSP/CSP pass tests required by the change
- docs: `docs/design/02_programming_surfaces.md`, `docs/todo/02_programming_surfaces.md`, example-local `README.md`

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added
- [x] documented fallback verification (`pytest -q`, focused example runs, `pre-commit run --all-files`)

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [x] update `docs/design/` for implemented behavior
- [x] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land WSP/CSP surface builders
3. rewrite flagship examples and tests
4. sync docs
5. rebase, review, and merge

## Review Notes

Reviewers should inspect the surface from a human-first angle, not only a schema-correctness angle. If the new examples still read like payload assembly or trivial kernels hidden behind helpers, the PR is not done.
