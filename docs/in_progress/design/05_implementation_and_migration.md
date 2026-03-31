# Implementation and Migration

## Implementation target

This redesign is not a compatibility layer over the current system. It is a
replacement of the current semantic substrate.

The implementation target is:

- `ProgramModule` as semantic owner
- typed node/aspect/analysis substrate
- normalized HTP Python builder/renderer loop
- interpreter registry over typed objects
- dialect registry for builtin and extension dialects
- compact stage artifacts using `program.py`, `stage.json`, `state.json`

Implementation style is part of the target:

- new IR code should minimize stringly-typed semantic references
- new IR code should minimize dict-shaped semantic ownership
- new IR code should prefer typed Python objects and object-oriented ownership
  over monolithic procedural payload assembly

## No-legacy law

Migration must follow one strict law:

> No legacy parallel substrate is allowed to survive after the redesign lands.

That means:

- no old payload-first semantic path left active alongside `ProgramModule`
- no duplicate renderer/replay system preserved “for compatibility”
- no old pass result contracts kept alive if the new contract replaces them
- no sidecar-only semantic ownership left in parallel with typed objects

Transitional adapters may exist only inside the feature branch while migrating.
They must be removed before merge.

## Implementation slices

### 1. Core substrate

Introduce:

- core node base classes
- `ProgramModule`
- identity/scope/binding/region types
- dialect registry

### 2. Builder and renderer

Introduce:

- normalized Python builder
- normalized Python renderer
- semantic equivalence checks

### 3. Interpreter registry

Introduce:

- shared expression/statement interpreter substrate
- top-level interpreters for `Kernel`, `Routine`, `TaskGraph`,
  `ProcessGraph`

### 4. Pass and commit system

Replace:

- pass input/output contract
- invalidation/preservation tracking
- commit-time validation
- compact stage artifact emission

### 5. Frontend migration

Rebuild:

- `htp.kernel`
- `htp.routine`
- `htp.wsp`
- `htp.csp`

on the new frontend-definition substrate.

### 6. Dialect migration

Port builtin and extension dialects onto:

- common node/aspect/intrinsic registration
- common interpreter hooks
- common artifact/commit rules

### 7. Example and test migration

Rewrite flagship examples and contract tests to prove:

- native Python authoring
- normalized staged Python readability
- rebuildability
- executability after non-trivial passes

## Migration order

Recommended order:

1. semantic owner + identity substrate
2. builder/renderer
3. interpreter substrate
4. pass result / commit validation
5. one frontend end-to-end
6. remaining frontends
7. dialect and extension migration
8. example/test cleanup
9. delete all replaced legacy paths

## Required proof points

Before merge, this branch should prove:

- normalized `program.py` is the primary review/replay artifact
- `program.py` rebuilds an equivalent `ProgramModule`
- pass commits enforce the new stage contract
- at least one non-trivial frontend/pipeline path runs entirely on the new
  substrate
- legacy substrate code has been removed, not merely bypassed

## Current status audit

This section records what is actually implemented today, not only the intended
end state.

### Implemented

- `ProgramModule` now owns committed stage state.
- `ProgramModule` now stores typed `KernelIR` / `WorkloadIR` objects for those
  semantic surfaces and serializes them only at artifact boundaries.
- committed-stage aspects now use typed wrapper objects instead of raw dict
  ownership for:
  - `types`
  - `layout`
  - `effects`
  - `schedule`
- committed-stage identity payloads now use typed wrappers for:
  - entity tables
  - binding tables
  - rewrite maps
- committed-stage analyses now use typed `AnalysisRecord` wrappers instead of
  raw dict ownership
- `htp.kernel.KernelSpec`, `htp.routine.ProgramSpec`,
  `htp.wsp.WSPProgramSpec`, and `htp.csp.CSPProgramSpec` now lower to
  `ProgramModule` directly through `to_program_module()`, and
  `compile_program()` prefers that path.
- a first dialect-registry slice exists for builtin frontend dialects, and the
  public frontends now record their active dialect set in `ProgramModule.meta`
- committed stages emit the compact contract:
  - `program.py`
  - `stage.json`
  - `state.json`
- staged `program.py` reconstructs `ProgramModule` and executes through
  `ProgramModule.run(...)`
- pass contracts and traces record Python renderability/executability
  preservation at committed stage boundaries
- the default pipeline now keeps committed pass state as `ProgramModule`
  objects rather than only dict payloads

### Partial

- `ProgramModule` now uses typed analysis records, but not the fuller
  typed/dialect-aware analysis substrate planned in `02_ir_structure.md`
- the first typed-node slice now exists under:
  - `htp.ir.nodes`
  - `htp.ir.node_exec`
  - `htp.ir.build`
  but it currently covers only a small kernel-oriented subset
- the current interpreter path proves the executable contract, but it is still
  registry-and-payload-oriented rather than the final typed-node interpreter
  substrate
- public frontends now enter through `ProgramModule`, but they still target the
  older semantic payload shapes internally and have not yet been rebuilt on a
  common frontend-definition substrate

### Not implemented yet

- the common typed `Node` / `Item` / `Expr` / `Stmt` / `Region` hierarchy
- the fuller dialect packaging/activation model described in
  `03_dialects_and_frontends.md`
- migration of the public frontends onto the final common node/front-end
  definition substrate
- full extension migration onto dialect-owned nodes/aspects/intrinsics

## Validation example

The minimal proof example for the implemented slice should cover:

1. direct `ProgramModule` definition
2. execution through a registered interpreter
3. transformation into a new `ProgramModule`
4. render/import round-trip through staged `program.py`

That example is tracked by `tests/ir/test_program_module_flow.py`.

What that test proves today:

- a typed `ProgramModule` can be defined directly without going through the old
  payload-only stage path
- execution dispatches through `ProgramModule.run(...)` and the interpreter
  registry
- a pass-style transformation can rewrite the module and preserve staged
  replayability
- rendered staged Python rebuilds an equivalent `ProgramModule`

The branch also needs a human-facing acceptance example under `examples/` that
proves the same flow without test-style payload assembly. That example should
become part of the merge criteria for this PR.

That acceptance example now lives at:

- `examples/ir_program_module_flow/demo.py`
- `examples/ir_program_module_flow/README.md`

## Documentation sync before merge

Before merge:

- sync the validated redesign into `docs/design/`
- update `docs/todo/`
- remove this feature's files from `docs/in_progress/`
- ensure no documentation claims the legacy substrate still exists
