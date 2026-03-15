# Tile/View and Loop-Index Surface

- ID: `027-tile-view-loop-surface`
- Branch: `htp/feat-tile-view-loop-surface`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Add Python-native tile/view slicing and semantic loop-index objects to the public kernel surface so staged GPU mainloops can be written as real indexed programs instead of whole-buffer placeholder choreography. The feature must be large enough to rewrite at least one flagship WSP example and make loop indices participate in actual view construction.

## Why

- contract gap: `docs/todo/programming_surfaces.md` still calls out tile/view slicing and loop-index semantics as the first remaining programming-surface gap
- user-facing impact: current staged GEMM examples still copy whole buffers into stage slots instead of expressing concrete tile views
- architectural reason: index-aware views should stay on the shared `htp.kernel` surface, not be introduced as a backend-owned DSL

## Scope Checklist

- [x] add first-class tile/view slicing on native kernel values
- [x] make loop indices semantic objects that can participate in slice expressions
- [x] rewrite at least one flagship WSP example and tests to use real tile views
- [x] sync `docs/design/` and narrow `docs/todo/programming_surfaces.md`

## Code Surfaces

- producer: `htp/kernel.py`, `examples/wsp_warp_gemm/`, `examples/wsp_littlekernel_pipelined_gemm/`
- validator/binding: semantic payload consumers in `htp/passes/program_model.py`
- tests: `tests/test_public_surfaces.py`, `tests/examples/test_examples.py`
- docs: `docs/design/programming_surfaces.md`, `docs/todo/programming_surfaces.md`, `docs/todo/README.md`

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added
- [x] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land tile/view and loop-index substrate changes
3. rewrite examples and tests
4. sync docs
5. rebase, review, and merge

## Review Notes

Reviewers should check whether slicing and loop indices stay on the shared HTP surface instead of becoming a hidden sidecar IR, and whether the rewritten examples are semantically more meaningful instead of only syntactically shorter.

## Progress Notes

- added Python slice-based tile/view authoring on `KernelValue` so staged kernels can write `A[:, k0:k0+16]` and `B[k0:k0+16, :]`
- promoted loop variables from pure trace annotations into semantic index objects that preserve symbolic expressions while remaining usable as Python indices
- rewrote the flagship WSP GEMM examples and their regression tests around indexed tile views instead of whole-buffer placeholder copies

## Verification Evidence

- local fallback verification used because `pixi` is not installed in this shell
- `pytest -q tests/test_public_surfaces.py tests/examples/test_examples.py`
- `pytest -q`
- `pre-commit run --all-files`
