# HTP (Heterogeneous Tile Programming) — Feature Catalog (WHAT)

## 0. Feature principles

- **Extensibility-first**: every major axis must be extensible (dialects, intrinsics, layout facets, passes, pipelines, backends, bindings).
- **Typed composition**: extension compatibility is checked via `requires/provides` capability typing plus layout/effect typing.
- **Artifact-first**: compilation output is always a package with a manifest and inspectable intermediate dumps.
- **AST-first**: Python AST is the base IR; optional external compilation islands are explicit.

### 0.1 Core type system (minimum, shared across dialects)

HTP needs a small, stable type system that all dialects build on:

- scalars: `i{8,16,32,64}`, `u{8,16,32,64}`, `f16`, `bf16`, `f32`, `f64`, `bool`
- indices/sizes: `Index`, `Dim`, `Sym("M")` style symbolic dimensions
- tiles/tensors:
  - `Tile[m, n, dtype]` (value-level tile in registers or local scratch)
  - `Tensor[shape..., dtype]` (logical tensor; may carry layout facets)
- memory references/buffers:
  - `Buffer[shape..., dtype, space]` where `space ∈ {global, smem, ub, lds, sram, ...}`

Layout facets and effects refine these types; dialects must not invent incompatible “parallel worlds” of types.

---

## 1. Programming entry (Python)

### 1.1 Kernel programming (tile-level)

- `@kernel` defines a tile kernel with a typed signature.
- Kernel bodies call intrinsics (portable or backend-specific) such as:
  - arithmetic/elementwise
  - loads/stores
  - asynchronous copies, barriers, events
- Kernel parameters can carry:
  - element dtype
  - tile shape
  - layout facets (distribution/memory/hardware constraints)

Rationale: kernels are the reusable unit for megakernels and pipelines.

Design decision (extensibility): `@kernel` is *not* a compiler hardcode. It is provided by a default dialect package
(`Dialect.CoreKernel`) and is replaceable/extendable via the dialect registry. All kernel dialects must lower into the
canonical `KernelDef` AST form (see `docs/design/impls/01_ir_model.md`).

### 1.2 WSP: workload vs schedule programming

Two interlocked but separate layers:

- **Workload**: pure declarative definition of tasks and logical parallelism.
- **Schedule**: explicit, composable directives that constrain mapping, fusion, pipelining, buffering, and resource use.

Rationale: preserve the “workload first; schedule later” workflow across backends.

Design decision: WSP is a dialect package. It defines syntax (`@workload`, `@schedule`) plus typing rules and
canonicalization/lowering passes into a canonical WSP graph/loop form.

### 1.3 CSP: process/channel pipelines

- Processes with typed channels (bounded FIFO / rendezvous events).
- Static typing for:
  - stream element types
  - capacity/packing constraints (backend-dependent)
  - linear/affine usage to prevent deadlock / mismatch (Dato-style).

Rationale: pipelines are the natural representation for megakernels and serving routines.

Design decision: CSP is a dialect package. It defines process/channel syntax and effect typing rules, and it must lower
into a canonical CSP graph form consumable by backends.

### 1.4 Serving routine programming (host orchestration)

- A “routine” is a program that composes:
  - backend-built kernels/megakernels
  - data movement
  - CSP pipelines
  - runtime dispatch decisions (e.g., batch splitting, dynamic shapes)

Rationale: serving is “things above kernels” and must be in scope.

Design decision: “serving routines” are not a separate dialect. They are compositions of CoreKernel + WSP + CSP plus
ordinary Python orchestration constructs, with explicit compilation boundaries.
---

## 2. Layout system (unified, multi-facet)

### 2.1 Distribution facet (Dato/Axe)

- Per-dimension distribution elements:
  - Shard on a mesh axis
  - Replicate
- Join/compatibility rules and explicit relayout operations.
- Effect tracking for collectives (e.g., pending reductions that must be discharged).

### 2.2 Memory facet (Triton/CuTe)

- Strides/order/swizzle/pack as a physical memory description.
- Composition operations (tile, reshape, permute) that remain explicit.

### 2.3 Hardware facet (Arknife-style)

- Explicit hardware hierarchy:
  - parallel levels (grid/block/warp/tile or backend equivalents)
  - memory spaces with capacity/alignment constraints

Rationale: backends differ; layout must bridge distributed ↔ on-device ↔ runtime constraints.

Design decision: layout is integrated as **typed metadata** attached to tensors/tiles/buffers, refined by passes. Cross-
backend portability is achieved by:

- a single *facet product model* (distribution ⊗ memory ⊗ hardware),
- explicit relayout operations (never silent “magical conversion”),
- backend-declared supported facet subsets and legality rules,
- and pipeline selection that chooses which facet refinements are available on a target.

---

## 3. Intrinsics & dialect libraries

### 3.1 Intrinsic sets with typed contracts

Intrinsics are declared with:

- collection naming
- semantic meaning (e.g., “vector add” on tiles),
- layout constraints (required facets),
- backend handler availability (which backend provides lowering/emitters).

### 3.2 Dialects as pluggable semantic layers

Dialects are packages that:

- define AST constructs / decorators / helper APIs,
- define typing rules / legality,
- define canonicalization/lowering passes into **canonical AST forms** (CoreKernel/WSP/CSP canonical nodes)
- optionally define analysis-time helper data structures (dialect-local), but they must be serializable and derived from
  the canonical forms + metadata.

Rationale: CSP and WSP should be optional and independently evolvable.

---

## 4. Pass system and compiler pipeline

### 4.1 AST passes (primary)

- Match/apply on AST with attached metadata.
- Each pass declares `requires/provides` capabilities and invariants.

### 4.2 External compilation islands (optional)

- A pass can lower a region into:
  - MLIR module(s) + dialects
  - external toolchain invocations
- The pass also defines how artifacts rejoin the main pipeline (manifested outputs).

Design decision: islands are defined via an explicit interface:

- an island pass declares:
  - a matcher (which AST regions it can “enter”),
  - an exporter (AST → external IR/tool inputs),
  - an importer (external outputs → HTP artifact references + typed stubs),
  - and an artifact contract (what files it emits and how they are named/manifested).

This keeps island semantics auditable and makes retargeting explicit.

### 4.3 Pipeline selection via capability typing

- A “target backend” selects a **pipeline template**.
- The pipeline is instantiated only if:
  - required dialects are present,
  - intrinsic handlers exist,
  - layout/effect typing is satisfied.

Rationale: extensibility without “if backend == …” branching.

---

## 5. Backends and artifacts

### 5.1 Backend abstraction

A backend defines:

- hardware model + supported layout facets,
- accepted dialects and required lowerings,
- artifact packaging contract,
- binding interface (build/run/simulate).

### 5.2 Artifact-first packaging

Each compile emits:

- `manifest.json` (or equivalent) describing:
  - inputs, versions, enabled dialects, pipeline, pass list
  - backend target and hardware model
  - produced artifact set and entrypoints
- `ir/` dumps and pass snapshots
- `codegen/` backend outputs

Rationale: reproducibility, debugging, and stable runtime integration.

Design addition: because the canonical IR is Python AST, HTP should also emit a **runnable Python replay program** at
each stage (`ir/stages/<id>/program.py`). This makes intermediate dumps executable “context packs”.

Design constraint:

- stage programs are always runnable in `mode="sim"` (they may be stubbed with explicit diagnostics for accelerated
  regions), which constrains what intermediate IR forms can exist.

---

## 6. “Must-support” targets (initial)

### 6.1 Ascend PTO ecosystem

- Emit artifacts consumable by a PTO runtime/toolchain (simulation and device).
- Packaging should mirror proven patterns (kernel/orchestration separation + manifest).

### 6.2 AIE via MLIR-AIE

- Emit MLIR-AIE oriented artifacts:
  - compute tile mapping, FIFO/stream wiring, host runtime glue
- Reuse known mapping concepts (kernel grid mapping + layout annotations).

---

## 7. Debuggability and introspection

- Standard pass tracing (“before/after” dumps).
- Type-check diagnostics:
  - layout incompatibility
  - stream protocol mismatches
  - missing backend handlers/capabilities
- Optional execution tracing hooks in bindings.

---

## 8. Deep dives index

Feature deep dives live in:

- `docs/design/feats/01_extensibility.md`
- `docs/design/feats/02_dialects_wsp.md`
- `docs/design/feats/03_dialects_csp.md`
- `docs/design/feats/04_intrinsics.md`
- `docs/design/feats/05_layout.md`
- `docs/design/feats/06_passes_pipelines.md`
- `docs/design/feats/07_backends_artifacts.md`
- `docs/design/feats/08_binding_runtime.md`
- `docs/design/feats/09_debuggability.md`
- `docs/design/feats/10_agentic_development.md`
