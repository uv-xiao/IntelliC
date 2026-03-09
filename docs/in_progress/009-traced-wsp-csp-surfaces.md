# Traced WSP/CSP Surfaces and Harder Flagship Examples

- ID: `009-traced-wsp-csp-surfaces`
- Branch: `htp/feat-traced-wsp-csp-surfaces`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Replace the remaining payload-shaped WSP/CSP public authoring with traced, human-written Python surfaces and upgrade the flagship WSP/CSP examples so they demonstrate real pattern intent rather than `store(C, A @ B)` plus metadata wrappers. Expand the design document for programming surfaces so it explains the surface model, extension points, and how new frontends should plug into the AST-centric compiler.

## Why

- contract gap: `htp.wsp` and `htp.csp` still feel like thin payload helpers rather than real Python-native frontends
- user-facing impact: current WSP/CSP examples do not show why HTP is a good programming system; they only show that the compiler can accept metadata
- architectural reason: without a clear traced-surface design and extension story, new frontends will drift back into ad-hoc dict emitters

## Scope Checklist

- [ ] add traced WSP/CSP program surfaces that record tasks/channels/processes from ordinary Python
- [ ] rewrite the flagship WSP/CSP examples onto those traced surfaces with stronger pattern content
- [ ] strengthen tests around the new traced authoring rules and malformed usage
- [ ] rewrite `docs/design/layers/02_programming_surfaces.md` with detailed surface design and extension guidance
- [ ] update `docs/todo/` to narrow the programming-surface gap
- [ ] remove this file from `docs/in_progress/` before merge

## Code Surfaces

- producer: `htp/wsp/__init__.py`, `htp/csp/__init__.py`, possibly `htp/kernel.py` / `htp/routine.py`
- compiler integration: `htp/compiler.py`, `htp/passes/program_model.py`
- tests/examples: `tests/test_public_surfaces.py`, `tests/examples/test_examples.py`, `examples/wsp_*`, `examples/csp_*`
- docs: `docs/design/layers/02_programming_surfaces.md`, `docs/design/examples/`, `docs/todo/`, `AGENTS.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test for traced WSP/CSP authoring
- [ ] one malformed-input / contract-violation test for the new surface
- [ ] one regression test showing the new surface removes an old awkward pattern
- [ ] human-friendly flagship examples updated or added
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land traced WSP/CSP surface changes
3. land tests and example rewrites
4. rewrite programming-surface docs
5. rebase, review, and merge

## Review Notes

Review the examples and `docs/design/layers/02_programming_surfaces.md` with public-language quality in mind. If the new surface still reads like payload assembly or thin wrappers over dicts, the PR has not met its goal.
