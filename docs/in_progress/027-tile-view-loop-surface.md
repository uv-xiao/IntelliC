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

- [ ] add first-class tile/view slicing on native kernel values
- [ ] make loop indices semantic objects that can participate in slice expressions
- [ ] rewrite at least one flagship WSP example and tests to use real tile views
- [ ] sync `docs/design/` and narrow `docs/todo/programming_surfaces.md`

## Code Surfaces

- producer: `htp/kernel.py`, `examples/wsp_warp_gemm/`, `examples/wsp_littlekernel_pipelined_gemm/`
- validator/binding: semantic payload consumers in `htp/passes/program_model.py`
- tests: `tests/test_public_surfaces.py`, `tests/examples/test_examples.py`
- docs: `docs/design/programming_surfaces.md`, `docs/todo/programming_surfaces.md`, `docs/todo/README.md`

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
2. land tile/view and loop-index substrate changes
3. rewrite examples and tests
4. sync docs
5. rebase, review, and merge

## Review Notes

Reviewers should check whether slicing and loop indices stay on the shared HTP surface instead of becoming a hidden sidecar IR, and whether the rewritten examples are semantically more meaningful instead of only syntactically shorter.
