# Loop and Scratch Programming Surfaces

- ID: `025-loop-scratch-surfaces`
- Branch: `htp/feat-loop-scratch-surfaces`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Add native loop/region authoring and explicit scratch/memory-scope declarations to the public kernel surface so HTP examples can express staged mainloops without constructor soup, raw string scratch names, or manual repeated copies. The feature should be large enough to reauthor at least one flagship GEMM-style example and strengthen the public-surface tests around those patterns.

## Why

- contract gap: `docs/todo/programming_surfaces.md` still lists loop/region authoring and scratch/memory-scope authoring as open gaps
- user-facing impact: current mainloop-style examples still rely on repeated manual temporaries instead of readable staged loops and declared scratch storage
- architectural reason: HTP should absorb LittleKernel/PyPTO readability lessons through one shared kernel surface, not by leaving low-level patterns to backend-specific frontends

## Scope Checklist

- [ ] add explicit scratch-buffer / scratch-array helpers on native kernel values
- [ ] add traced loop / region helpers that annotate repeated kernel ops without leaving Python-space
- [ ] rewrite at least one flagship WSP-style example and its tests onto the new surface
- [ ] sync `docs/design/` and narrow `docs/todo/programming_surfaces.md`

## Code Surfaces

- producer: `htp/kernel.py`, `examples/wsp_littlekernel_pipelined_gemm/`, `examples/wsp_warp_gemm/`
- validator/binding: semantic payload consumers in `htp/passes/program_model.py`
- tests: `tests/test_public_surfaces.py`, `tests/examples/test_examples.py`, `tests/pipeline/`
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
2. land loop/scratch surface primitives
3. reauthor tests and flagship examples
4. sync docs
5. rebase, review, and merge

## Review Notes

Reviewers should check whether the new surface genuinely improves authored readability and whether loop/scratch metadata stays on the shared HTP surface instead of creating a sidecar semantic path.
