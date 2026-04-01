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
- `06_pr_closure_proof.md`
  - canonical proof example, pass chain, interpreter requirements, and the
    concrete merge bar for closing PR `#67`
- `08_module_organization_and_code_quality.md`
  - repository-wide ownership model, code-quality rules, and the refactor-first
    module-organization contract for this branch

## Frozen principles

- HTP must be both human-friendly and LLM-friendly.
- The route is AST all the way.
- The semantic owner is a typed Python object graph rooted at `ProgramModule`.
- Every committed stage must render to normalized HTP Python and remain
  executable or fail via structured replay diagnostics.
- Builtin and extension features are both dialects using the same substrate.
- Legacy parallel systems are not allowed to survive the migration.
- Module ownership must be explicit; stringly semantic linkage and dict-owned
  semantics are not acceptable end states for the redesigned substrate.

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
  - now covering kernel, task-graph, and process-graph items with typed ids
- `ProgramModule` now owns typed `KernelIR` / `WorkloadIR` objects rather than
  raw dicts for those semantic surfaces
- committed-stage aspects now use typed wrappers instead of raw dict ownership
- committed-stage identity payloads now use typed wrappers instead of raw dict
  ownership
- committed-stage analyses now use typed records instead of raw dict ownership
- `htp.kernel.KernelSpec`, `htp.routine.ProgramSpec`,
  `htp.wsp.WSPProgramSpec`, and `htp.csp.CSPProgramSpec` now expose
  `to_program_module()`, and `compile_program()` prefers the `ProgramModule`
  path over `to_program()`
- those public frontends now share common frontend builder helpers in
  `htp/ir/frontend.py` (workload assembly, dialect activation metadata, and
  `ProgramModule` construction)
- a rule-backed frontend-definition substrate now exists in
  `htp/ir/frontend_rules.py`
- builtin public surfaces are resolved through registered `FrontendSpec` objects
  in `htp/ir/frontends.py` (`resolve_frontend(...)`, `ensure_builtin_frontends()`)
  and compiler ingress routes through `FrontendSpec.build(...)` in
  `htp/compiler.py`
- builtin `htp.kernel`, `htp.routine`, `htp.wsp`, and `htp.csp` public
  surfaces are now all registered as `rule=`-backed frontend specs rather than
  direct `build_program_module=` callbacks
- `to_program_module()` on routine/WSP/CSP now delegates back through the
  registered frontend rule instead of owning a parallel lowering path
- WSP and CSP public specs now use typed top-level surface objects rather than
  raw dict payload fields before serialization
- remaining gap: those rules still rebuild nested stage/process-step attrs
  rather than the final node-first rule/combinator frontend API
- a first dialect registry slice now exists for builtin frontend dialects, and
  public frontends record their active dialect set and activation manifest into
  `ProgramModule.meta`
- a human-facing IR definition / execution / transformation example under
  `examples/ir_program_module_flow/`

Still design-only or partial:

- the full typed node hierarchy in `02_ir_structure.md` beyond the current
  kernel/task-graph/process-graph slice
- the final node-first frontend substrate in `03_dialects_and_frontends.md`
  beyond the current `FrontendRule` / `FrontendSpec.build(...)` substrate
- the full typed analysis substrate beyond the current generic record wrapper
- full dialect migration beyond the current builtin frontend set
- extension and dialect migration beyond the current public frontend set
- the PR-closing tile-streamed GEMM proof directory and its four committed
  variant modules described in `06_pr_closure_proof.md`

So the redesign is not fully finished yet. The stage/execution contract slice
is implemented; the full IR-definition and dialect-definition substrate is not.
