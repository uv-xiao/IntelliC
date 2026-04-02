# PR Closure Proof

This document defines the closure target for PR `#67`
(`htp/feat-ast-all-the-way-contracts`).

It answers one specific question: what has to become real in the codebase for
the AST-all-the-way redesign to be considered implemented rather than only
partially scaffolded.

## Closure boundary

This PR does **not** need to implement every future HTP feature.

It does need to implement every feature required by the AST-all-the-way
redesign itself:

- a typed object-owned IR substrate rooted at `ProgramModule`
- object-oriented execution over that substrate
- rule-backed frontend construction
- typed pass-to-pass transformation over committed `ProgramModule` variants
- normalized Python artifacts that rebuild equivalent typed objects
- one end-to-end proof example that exercises the redesigned flow honestly

The canonical proof example is therefore an **acceptance target**, not an
optional demo.

## Canonical proof example

The canonical acceptance example is a **tile-streamed GEMM pipeline** that
combines:

- kernel computation
- WSP task/schedule structure
- CSP process/channel structure
- non-trivial pass rewrites
- interpreter execution at each committed variant

This example is chosen because it exercises the hardest remaining integration
point in the redesign:

- kernel IR
- workload/task IR
- process/protocol IR
- scheduling facts
- backend-ready discharge form

A proof that covers only one of those is not enough to close the PR.

## Required committed variants

The canonical example must exist in four committed variants:

1. `surface_program.py`
   - handwritten, human-first authored surface code
2. `core_ir.py`
   - explicit normalized HTP Python rebuilding the typed core IR
3. `scheduled_ir.py`
   - explicit normalized HTP Python rebuilding the pass-rewritten scheduled IR
4. `backend_ready_ir.py`
   - explicit normalized HTP Python rebuilding the backend-discharge-ready IR

All four variants must:

- rebuild a `ProgramModule`
- be readable normalized HTP Python
- be runnable through `ProgramModule.run(...)`
- align with emitted staged artifacts closely enough to reparse into equivalent
  typed objects

The example should live in one example directory with a local `README.md` and a
small driver script. The staged artifacts remain important, but they are not a
substitute for explicit human-facing proof modules.

## Canonical proof substrate

All four variants lower into and transform between the same canonical substrate:

- one shared typed object graph rooted at `ProgramModule`
- top-level items:
  - `Kernel`
  - `TaskGraph`
  - `ProcessGraph`
- shared node core:
  - `Node`
  - `Item`
  - `Expr`
  - `Stmt`
  - `Region`
- typed identity, bindings, scopes, and refs
- aspects for:
  - types
  - layout
  - effects
  - schedule
  - backend-ready discharge facts

This means the surface-authored variant is not a separate semantic world. It is
simply a different frontend route into the same canonical `ProgramModule`
substrate.

## IR coverage required for the proof

The canonical proof needs these typed IR forms in code.

### Kernel IR

- buffer, view, load, store
- scalar/index arithmetic
- loops and regions
- slice/tile/view nodes
- staged scratch/storage nodes
- matmul or MMA-style compute nodes
- explicit send/recv/barrier-style behavior through dialect intrinsics

### WSP-facing typed structure

- typed task nodes
- typed dependency edges
- typed stage blocks
- typed schedule objects for:
  - tiling
  - role assignment
  - pipeline depth
  - resource facts

### CSP-facing typed structure

- typed process nodes
- typed channel nodes
- typed step nodes for:
  - receive
  - compute
  - send
- typed protocol facts carried as aspects

### Backend-ready form

The backend-ready form must still be:

- a `ProgramModule`
- normalized HTP Python
- interpreter-runnable

It may carry backend-ready intrinsics or discharge hints, but those must remain
Python-owned typed objects or typed aspects, not foreign textual ownership.

## Pass chain required for closure

The PR closes on one fixed typed-object pass chain:

1. **Surface-to-core normalization**
   - lowers authored surface objects into the shared typed node core
   - removes remaining payload-shaped nested stage/process-step structure for
     the canonical path

2. **Tile-and-stage rewrite**
   - rewrites plain GEMM into tiled buffers/views, staged tasks, and staged
     processes

3. **Schedule/protocol enrichment**
   - adds typed schedule objects and typed protocol/process facts

4. **Backend-ready rewrite**
   - rewrites into backend-discharge-ready typed objects and typed intrinsics
   - remains Python-owned and interpreter-runnable

Each committed variant of the canonical example must correspond to one point in
this chain and must remain rebuildable and executable.

## Interpreter architecture requirement

The execution mechanism must be object-oriented.

The accepted architecture is:

- one public entry:
  - `ProgramModule.run(...)`
- one dispatcher layer selecting the active item/aspect execution path
- object-owned interpreter units beneath it:
  - `KernelInterpreter`
  - `TaskGraphInterpreter`
  - `ProcessGraphInterpreter`
  - `StmtExecutor`
  - `ExprEvaluator`
  - dialect intrinsic handlers
  - backend-ready handlers

Not acceptable:

- a monolithic all-purpose interpreter function
- raw AST-walking semantics as the primary execution path
- payload-dispatch execution that bypasses typed objects

The backend-ready variant may specialize execution behavior, but it must extend
the same object-oriented interpreter system rather than bypass it.

## Merge acceptance criteria

PR `#67` is ready to close only when all of the following are true.

### Example proof

- the canonical tile-streamed GEMM example exists in one example directory
- it contains:
  - `surface_program.py`
  - `core_ir.py`
  - `scheduled_ir.py`
  - `backend_ready_ir.py`
  - `README.md`
  - a small driver/demo

### Execution proof

- each module rebuilds a `ProgramModule`
- each module runs through `ProgramModule.run(...)`
- execution uses the object-oriented interpreter stack

### Transformation proof

- tests prove:
  - surface → core
  - core → scheduled
  - scheduled → backend-ready
- each transition preserves rebuildability and executability at the committed
  boundary

### Artifact proof

- emitted staged `program.py` for each committed variant matches the normalized
  checked-in module form closely enough to reparse into equivalent
  `ProgramModule` objects
- `stage.json` and `state.json` stay aligned with those modules

### Legacy cleanup proof

- no parallel payload-first lowering path remains for the redesigned frontend
  route
- no nested WSP/CSP stage/process-step semantics remain owned only by dict
  payloads for the canonical path

### Documentation proof

The following documents must be synchronized to the final implementation:

- `docs/design/compiler_model.md`
- `docs/design/programming_surfaces.md`
- `docs/design/artifacts_replay_debug.md`
- `docs/in_progress/028-ast-all-the-way-contracts.md`

## Remaining gap after current branch state

Relative to the current branch, the main open work to reach closure is:

- finish the common typed node hierarchy beyond the current first slice
- type nested WSP stage structure and CSP process-step structure end to end
- make the pass chain real over those typed objects
- build the canonical tile-streamed GEMM proof directory with the four explicit
  committed variants
- connect emitted staged variants to those explicit checked-in normalized
  modules
- finish the object-oriented interpreter structure for those committed variants

This is the work that should drive the final implementation plan for closing
PR `#67`.
