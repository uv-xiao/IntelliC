# AST-All-the-Way Redesign

This directory is the design collection for PR `#67`
(`htp/feat-ast-all-the-way-contracts`).

It replaces the previous single long note with a small set of focused design
documents. Together they define the joint redesign of:

- programming surfaces
- the IR/object model
- staged artifacts and replay
- dialect/extensibility structure
- pass and commit contracts
- implementation and migration rules

## Documents

- `01_foundations.md`
  - project goal, normalized Python contract, `ProgramModule`, and the
    executability rule
- `02_ir_structure.md`
  - node model, identity/binding/scope/region model, core type/value split
- `03_dialects_and_frontends.md`
  - dialect model, optional frontend-definition mechanism, intrinsic registry
- `04_passes_and_artifacts.md`
  - aspects/analyses, invalidation, pass API, stage commit, compact artifact
    layout
- `05_implementation_and_migration.md`
  - implementation-facing targets, migration order, and the no-legacy law

## Frozen principles

- HTP must be both human-friendly and LLM-friendly.
- The route is AST all the way.
- The semantic owner is a typed Python object graph rooted at `ProgramModule`.
- Every committed stage must render to normalized HTP Python and remain
  executable or fail via structured replay diagnostics.
- Builtin and extension features are both dialects using the same substrate.
- Legacy parallel systems are not allowed to survive the migration.

## Implementation rule

This collection is not only explanatory. It is the contract for the next code
changes on this branch. Implementation should follow these documents, and the
validated results must be synced into `docs/design/` before merge.

## Current implementation audit

This collection is ahead of the current codebase.

Implemented on this branch:

- `ProgramModule` as the committed-stage semantic owner
- compact staged artifacts: `program.py`, `stage.json`, `state.json`
- interpreter-backed staged replay through `ProgramModule.run(...)`
- pass-contract preservation flags for Python renderability/executability
- `ProgramModule`-backed in-memory pipeline state at committed pass boundaries
- first typed IR-node slice:
  - `htp.ir.nodes`
  - `htp.ir.node_exec`
  - `htp.ir.build`
- `ProgramModule` now owns typed `KernelIR` / `WorkloadIR` objects rather than
  raw dicts for those semantic surfaces
- committed-stage aspects now use typed wrappers instead of raw dict ownership
- committed-stage identity payloads now use typed wrappers instead of raw dict
  ownership
- `htp.kernel.KernelSpec`, `htp.routine.ProgramSpec`,
  `htp.wsp.WSPProgramSpec`, and `htp.csp.CSPProgramSpec` now expose
  `to_program_module()`, and `compile_program()` prefers the `ProgramModule`
  path over `to_program()`
- a human-facing IR definition / execution / transformation example under
  `examples/ir_program_module_flow/`

Still design-only or partial:

- the full typed node hierarchy in `02_ir_structure.md`
- the uniform dialect registry/frontends substrate in
  `03_dialects_and_frontends.md`
- extension and dialect migration beyond the current public frontend set

So the redesign is not fully finished yet. The stage/execution contract slice
is implemented; the full IR-definition and dialect-definition substrate is not.
