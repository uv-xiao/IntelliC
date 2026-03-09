# Frontend Surface Redesign from PyPTO and LittleKernel

- ID: `007-frontend-surface-redesign`
- Branch: `htp/feat-frontend-surface-redesign`
- PR: `https://github.com/uv-xiao/htp/pull/42`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Redesign the public HTP programming surface so flagship kernels and routines read at least as naturally as the reference surfaces in `references/pypto/python/pypto/language` and `references/triton-distributed-knowingnothing/python/little_kernel/language`. Land the new surface with a small set of rewritten flagship examples and the minimum compiler/runtime changes needed to support them.

## Why

- contract gap: current `htp.kernel` is better than raw dict payloads, but still too mechanical for larger programs
- user-facing impact: flagship examples still read like compiler demos, not like a human-first kernel language
- architectural reason: if the Python-native surface is weak, the AST-centric compiler claim is weak

## Scope Checklist

- [x] study and extract concrete surface patterns from `pypto.language` and `little_kernel.language`
- [x] redesign the HTP public kernel/routine surface around more native authoring patterns
- [x] rewrite 2–3 flagship examples onto the new surface
- [x] add focused contract and regression tests for the new surface
- [x] update `docs/design/` and narrow the corresponding TODOs
- [ ] remove this file from `docs/in_progress/` before merge

## Code Surfaces

- producer: `htp/kernel.py`, `htp/routine.py`, related frontend helpers
- compiler integration: `htp/compiler.py`, `htp/passes/program_model.py`
- examples/tests: `examples/`, `tests/examples/`, frontend-facing tests
- docs: `docs/design/`, `docs/todo/`

## Test and Verification Plan

Required:
- [x] one happy-path test for the redesigned surface
- [x] one malformed-input / contract-violation test
- [x] one regression test for a previously awkward or broken authoring pattern
- [x] human-friendly flagship examples updated
- [x] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. add failing/targeted frontend tests
3. land public-surface implementation
4. rewrite flagship examples
5. sync docs
6. rebase, review, and merge

## Review Notes

Review the public authoring ergonomics against the reference files, not only internal correctness. The point of this PR is to improve human-written code shape, not only to add more helper functions.
