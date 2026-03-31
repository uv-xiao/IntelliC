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
- builtin public surfaces are resolved through registered `FrontendSpec` objects
  in `htp/ir/frontends.py`, and `htp.compile_program(...)` routes ingress
  through `FrontendSpec.build(...)` in `htp/compiler.py`
- a rule-backed frontend-definition substrate now exists in
  `htp/ir/frontend_rules.py` and is used by `FrontendSpec.build(...)` to execute
  registered `FrontendRule` objects
- builtin `htp.kernel`, `htp.routine`, `htp.wsp`, and `htp.csp` public
  surfaces are now all registered as `rule=`-backed frontend specs rather than
  direct `build_program_module=` callbacks
- `to_program_module()` on routine/WSP/CSP now delegates back through the
  registered frontend rule instead of owning a parallel lowering body
- WSP and CSP public specs now use typed top-level surface objects instead of
  raw dict payload fields before serialization
- public frontend rules still reuse shared helpers in `htp/ir/frontend.py` for
  workload assembly, dialect activation metadata, and `ProgramModule`
  construction, and they still rebuild nested stage/process-step structure from
  payload-shaped attrs rather than the final node-first
  rule/combinator API
- a manifest-style dialect activation slice now exists for builtin frontend
  dialects, and the public frontends now record both active dialect closure and
  activation payloads in `ProgramModule.meta`
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
  and now covers kernel, task-graph, and process-graph items with typed ids and
  interpreter paths, but it still does not cover the fuller statement/control
  hierarchy planned in `02_ir_structure.md`
- the current interpreter path proves the executable contract, but it is still
  registry-and-payload-oriented rather than the final typed-node interpreter
  substrate
- the shared frontend-definition substrate now exists, but it still rebuilds
  nested workload/process stage attrs from payload-shaped fields instead of the
  final typed frontend-definition API described in
  `03_dialects_and_frontends.md`
- the frontend registry exists only for builtin public surfaces and still
  resolves primarily by Python surface type; the builtin public surfaces are
  now rule-backed, but the fuller node-first rule/combinator API described in
  `03_dialects_and_frontends.md` is not implemented yet
- dialect activation now handles dependency closure and activation payloads, but
  builtin and extension dialects have not yet been migrated onto the full
  node/aspect/intrinsic registration substrate described in
  `03_dialects_and_frontends.md`

### Not implemented yet

- the common typed `Node` / `Item` / `Expr` / `Stmt` / `Region` hierarchy
- the final node-first rule/combinator frontend-definition API described in
  `03_dialects_and_frontends.md`
- full extension migration onto dialect-owned nodes/aspects/intrinsics

## Code pointers (frontend-definition substrate)

- `htp/ir/frontend_rules.py` — `FrontendBuildContext`, `FrontendRule`, `FrontendRuleResult`
- `htp/ir/frontends.py` — `FrontendSpec`, registry, `resolve_frontend(...)`
- `htp/ir/frontend.py` — shared builder helpers for routine/WSP/CSP
- `htp/kernel.py` — first public surface with `rule=`-backed ingress
- `htp/compiler.py` — compiler ingress routes through `FrontendSpec.build(...)`

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
