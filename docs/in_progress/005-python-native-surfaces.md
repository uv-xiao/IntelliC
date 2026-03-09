# Python-Native Surfaces and Harder Flagship Examples

- ID: `005-python-native-surfaces`
- Branch: `htp/feat-python-native-surfaces`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Add a real public kernel/routine authoring surface so flagship examples and high-level tests are written as Python-native programs rather than raw program dicts or spec-constructor stacks, and raise the flagship examples to harder cases that better demonstrate scheduling, orchestration, and backend discharge.

## Why

- contract gap: `docs/todo/layers/02_programming_surfaces.md` still marks public authoring and example quality as incomplete
- user-facing impact: the current main examples still look like proof scaffolding rather than the intended programming model
- architectural reason: if HTP is Python-AST-centric, the public authoring surface has to look like Python-native code, not only serialized compiler payloads
- reference bar: `references/pypto/` and `references/arknife/` show the minimum readability level the public surface must reach

## Scope Checklist

- [x] remove stale `004-docs-depth-restoration.md` task state from `docs/in_progress/`
- [x] add a public kernel/routine authoring surface for high-level programs
- [x] make `compile_program(...)` accept the public surface objects
- [ ] broaden simple backend lowering/emission enough for multi-op flagship examples
- [x] rewrite flagship examples to use the new Python-native surface
- [x] deepen the serving-routine example into a richer first-class routine surface
- [x] update tests and docs/design + docs/todo accordingly
- [ ] remove this file from `docs/in_progress/` before merge

## Code Surfaces

- producer: `htp/compiler.py`, new public authoring modules, `examples/`
- validator/binding: backend lowerers/emitters if multi-op support changes package shape
- tests: `tests/examples/`, compiler and backend tests
- docs: programming surfaces and agent workflow quality docs

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the old dict-style flagship pattern or backend op limitation
- [x] human-friendly flagship examples updated
- [ ] `pixi run verify` or documented fallback

## Documentation Plan

- [x] update `docs/design/layers/02_programming_surfaces.md`
- [x] update `docs/design/examples/`
- [x] update `docs/todo/layers/02_programming_surfaces.md`
- [x] update `docs/todo/layers/06_agent_product_and_workflow.md`
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. add public authoring surface
3. broaden backend support for harder examples
4. rewrite examples and tests
5. sync docs and merge

## Review Notes

Review both API shape and example readability carefully. The main requirement is that the flagship examples must stop looking like top-level raw compiler payloads.
