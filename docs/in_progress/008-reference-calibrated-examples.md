# Reference-Calibrated Example Suite and Surface Review

- ID: `008-reference-calibrated-examples`
- Branch: `htp/feat-reference-calibrated-examples`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Broaden HTP’s public example suite so the flagship examples are calibrated against `references/pypto/`, `references/triton-distributed-knowingnothing/python/little_kernel/`, and `references/arknife/` rather than against compact smoke cases. Land the minimum public-surface improvements needed to make those examples read like human-written Python instead of constructor-heavy compiler demos.

## Why

- contract gap: the current public surface is better than raw dict payloads, but several flagship examples are still too small or too mechanical
- user-facing impact: examples are the first proof of HTP’s AST-centric claim, so weak examples make the framework look weaker than it is
- architectural reason: if WSP/CSP and harder activation examples cannot be written naturally, the Python-first frontend story is incomplete

## Scope Checklist

- [ ] add the minimum surface changes needed for more natural reference-calibrated examples
- [ ] add harder public examples calibrated against PyPTO, LittleKernel, and Arknife
- [ ] rewrite remaining dict-heavy public examples/tests where a human-facing surface should exist
- [ ] add the LittleKernel AST-centric comparison as tracked future work/documentation
- [ ] tighten agent guidance so reviews explicitly judge human friendliness and syntax prettiness
- [ ] update `docs/design/` and narrow the corresponding TODOs
- [ ] remove this file from `docs/in_progress/` before merge

## Code Surfaces

- producer: `htp/kernel.py`, `htp/routine.py`, `htp/wsp/`, `htp/csp/`
- backend/codegen: `htp/backends/pto/`, `htp/backends/nvgpu/`, solver declarations if new ops are surfaced
- examples/tests: `examples/`, `tests/examples/`, frontend-facing tests
- docs: `AGENTS.md`, `.agent/rules/*.md`, `docs/design/`, `docs/todo/`

## Test and Verification Plan

Required:
- [ ] one happy-path test for each newly added public example family
- [ ] one malformed-input / contract-violation test for any new frontend surface rule
- [ ] one regression test proving the new surface removes an awkward old pattern
- [ ] human-friendly flagship examples updated or added
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior and the expanded example suite
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land surface/runtime changes needed by the new examples
3. land new examples and tests
4. sync docs and agent guidance
5. rebase, review, and merge

## Review Notes

Reviewers should judge this PR by the public code shape first. Examples and high-level tests should be evaluated for readability, human-first syntax, and whether they compare favorably with the reference repos, not only for internal correctness.
