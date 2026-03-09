# LittleKernel comparison and next surface pass

- ID: `014-littlekernel-comparison-surface-pass`
- Branch: `htp/feat-littlekernel-comparison-surface-pass`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Finish the written AST-centric comparison against LittleKernel and use that analysis to drive one more concrete surface improvement pass in HTP. The result should close the remaining programming-surface TODO instead of leaving the comparison as disconnected research.

## Why

- contract gap: `docs/todo/02_programming_surfaces.md` still has one open item
- user-facing impact: the repository needs a clear explanation of what HTP keeps canonical that LittleKernel does not, and what syntax/authoring lessons HTP should still absorb
- architectural reason: HTP’s AST-first claim is only persuasive if the comparison is written down and tied to concrete surface changes

## Scope Checklist

- [ ] study the relevant LittleKernel and PyPTO reference surfaces
- [ ] write the full comparison report under `docs/todo/reports/littlekernel_ast_comparison.md`
- [ ] extract concrete surface requirements from that comparison
- [ ] implement at least one meaningful public-surface improvement implied by the comparison
- [ ] update examples/tests/docs to reflect the improvement
- [ ] close the programming-surface TODO entry in `docs/todo/02_programming_surfaces.md`

## Code Surfaces

- producer: `htp/kernel.py`, `htp/routine.py`, `htp/wsp/__init__.py`, `htp/csp/__init__.py`, and example demos if the comparison implies a surface change
- docs: `docs/design/02_programming_surfaces.md`, `docs/todo/02_programming_surfaces.md`, `docs/todo/reports/littlekernel_ast_comparison.md`, example-local `README.md`
- tests: targeted public-surface and example tests that defend the specific new improvement

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one regression test for the surface improvement
- [ ] one example updated to use the improved surface
- [ ] `pytest -q`
- [ ] `pre-commit run --all-files`

Do not add low-signal tests. The improvement should be visible in public authoring, not just internal plumbing.

## Documentation Plan

- [ ] update `docs/design/` for landed behavior
- [ ] update `docs/todo/` to remove the remaining programming-surface gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. write comparison and extract concrete requirements
3. land the next surface improvement
4. update examples/tests/docs
5. rebase, review, and merge
