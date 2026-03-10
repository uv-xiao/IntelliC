# Compiler Model Closure

- ID: `020-compiler-model-closure`
- Branch: `htp/feat-compiler-model-closure`
- PR: `TBD`
- Status: `planned`
- Owner: `Codex`

## Goal

Close the remaining breadth gaps in `docs/todo/compiler_model.md` so the
semantic core is no longer limited to the current fused-elementwise and
single-step routine envelope. This task broadens the shared operation set,
makes the public type surface richer and more explicit, deepens
collective/distribution semantics, and turns serving routines into a real
first-class semantic case rather than an example-only wrapper.

## Why

- contract gap: `docs/todo/compiler_model.md` still has partial and open items
  in the core semantic model.
- architecture reason: backend depth and stronger programming surfaces depend
  on a richer shared compiler model rather than more backend-local exceptions.
- user-facing reason: HTP should express and stage richer semantics in
  human-first Python while keeping the resulting artifacts explicit.

## Scope Checklist

- [ ] broaden the shared op/type surface beyond the current fused-elementwise mix
- [ ] make the user-facing type surface match the staged model more closely
- [ ] deepen collective/distribution semantics and discharge rules
- [ ] make serving-routine semantics first-class in staged workload artifacts
- [ ] close `docs/todo/compiler_model.md` and sync summary counts

## Code Surfaces

- semantic model: `htp/ir/semantics.py`, `htp/ir/types.py`, `htp/ir/op_specs.py`
- frontend/program lowering: `htp/kernel.py`, `htp/routine.py`, `htp/passes/program_model.py`
- legality: `htp/passes/typecheck_layout_effects.py`
- examples/tests: `examples/serving_routine/`, `tests/passes/`, `tests/pipeline/`, `tests/examples/`
- docs: `docs/design/compiler_model.md`, `docs/todo/compiler_model.md`, `docs/todo/README.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating gap
- [ ] a human-friendly example update or addition
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete semantic
contract.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. add focused tests for the missing semantic breadth
3. land compiler-model and frontend updates
4. sync examples and docs
5. rebase, review, and merge

## Review Notes

Reviewers should check that new frontend-facing types and routine semantics
remain human-friendly Python rather than constructor-heavy payload assembly,
and that collective/distribution checks stay explicit in emitted artifacts.
