# HTP (Heterogeneous Tile Programming) — Feature Catalog (WHAT)

This document describes the broader target feature surface, not only the parts
already implemented in `htp/`.

Status shorthand used below:

- **implemented**: backed by current code and `docs/design/`
- **partial**: some substrate exists, but the full feature surface here does not
- **future**: design target only

## 0. Feature principles

- **Extensibility-first**: every major axis must be extensible (dialects, intrinsics, layout facets, passes, pipelines, backends, bindings).
- **Typed composition**: extension compatibility is checked via `requires/provides` capability typing plus layout/effect typing.
- **Artifact-first**: compilation output is always a package with a manifest and inspectable intermediate dumps.
- **AST-first**: Python AST is the base IR; MLIR-based compilation flows are optional extensions, not native core IR.

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

Current status: **partial**.
- implemented: scalar/buffer/tensor-like semantic payloads and staged
  type/layout/effect state
- missing: the full shared user-facing type system and broader op/type surface

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

Current status: **partial**.

### 1.2 WSP: workload vs schedule programming

Two interlocked but separate layers:

- **Workload**: pure declarative definition of tasks and logical parallelism.
- **Schedule**: explicit, composable directives that constrain mapping, fusion, pipelining, buffering, and resource use.

Rationale: preserve the “workload first; schedule later” workflow across backends.

Design decision: WSP is a dialect package. It defines syntax (`@workload`, `@schedule`) plus typing rules and
canonicalization/lowering passes into a canonical WSP graph/loop form.

Current status: **partial**.

### 1.3 CSP: process/channel pipelines

- Processes with typed channels (bounded FIFO / rendezvous events).
- Static typing for:
  - stream element types
  - capacity/packing constraints (backend-dependent)
  - linear/affine usage to prevent deadlock / mismatch (Dato-style).

Rationale: pipelines are the natural representation for megakernels and serving routines.

Design decision: CSP is a dialect package. It defines process/channel syntax and effect typing rules, and it must lower
into a canonical CSP graph form consumable by backends.

Current status: **partial**.

### 1.4 Serving routine programming (host orchestration)

- A “routine” is a program that composes:
  - backend-built kernels/megakernels
  - data movement
  - CSP pipelines
  - runtime dispatch decisions (e.g., batch splitting, dynamic shapes)

Rationale: serving is “things above kernels” and must be in scope.

Design decision: “serving routines” are not a separate dialect. They are compositions of CoreKernel + WSP + CSP plus
ordinary Python orchestration constructs, with explicit compilation boundaries.

Current status: **future**.
---

## 2. Layout system (unified, multi-facet)

Current status: **partial**.
- implemented: staged layout/effect payloads and target-specific layout metadata
- missing: the full facet-product user/programming model and legality algebra

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

Current status: **partial**.

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

Current status: **partial**.
- implemented: pass contracts, staged analyses, replayable stages, one extension
  island path
- missing: capability-solved pipeline construction and the broader dialect
  lowering ecosystem

### 4.1 AST passes (primary)

- Match/apply on AST with attached metadata.
- Each pass declares `requires/provides` capabilities and invariants.

### 4.2 IR round-trip compilation islands (optional extension)

A pass supplied by an extension package can run an **internal round-trip island**:

- construct MLIR from Python AST
- run an explicit MLIR pass pipeline
- build back Python AST from transformed MLIR

Design decision: round-trip islands are defined via an explicit enter/exit interface:

- matcher (eligible AST subset)
- exporter (AST → MLIR + identity ledger)
- pass pipeline (MLIR passes)
- importer (MLIR → AST + explicit maps when needed)

See: `docs/design/impls/12_mlir_roundtrip_island.md`.

### 4.3 External toolchains (backend artifact emission extension)

External toolchains (vendor compilers, MLIR-AIE tooling, etc.) are integrated by emitting their required IR/artifacts
under `codegen/<backend>/...` and recording toolchain pins/contracts in the manifest.

This is not a “compilation island” in the IR sense; it is a codegen artifact boundary.

### 4.3 Pipeline selection via capability typing

- A “target backend” selects a **pipeline template**.
- The pipeline is instantiated only if:
  - required dialects are present,
  - intrinsic handlers exist,
  - layout/effect typing is satisfied.

Rationale: extensibility without “if backend == …” branching.

Current status: **partial**.

---

## 5. Backends and artifacts

Current status: **partial**.
- implemented: PTO + NV-GPU package emission, validation, build/run/replay
- future: broader backend set and richer extension-owned codegen/toolchain paths

### 5.1 Backend abstraction

A backend defines:

- hardware model + supported layout facets,
- accepted dialects and required lowerings,
- artifact packaging contract,
- binding interface (build/run/simulate).

### 5.2 Artifact-first packaging

Each compile emits:

- `manifest.json` describing:
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

## 6. “Must-support” targets (initial v1 proof)

### 6.1 Ascend PTO ecosystem

- Emit artifacts consumable by a PTO runtime/toolchain (simulation and device).
- Packaging should mirror proven patterns (kernel/orchestration separation + manifest).

### 6.2 NV-GPU (Ampere and Blackwell)

- Emit artifacts consumable by an NV-GPU binding and build/runtime path.
- Hardware modeling should follow the Arknife-style explicit hierarchy and memory-space approach.
- The same HTP core contracts must support both Ampere and Blackwell profiles through `hardware_profile`, not through a
  second compiler architecture.

### 6.3 Optional extension backends/toolchains

- AIE via MLIR-AIE
- Emit MLIR-AIE oriented artifacts:
  - compute tile mapping, FIFO/stream wiring, host runtime glue
- Reuse known mapping concepts (kernel grid mapping + layout annotations).

Current status: **partial**.

---

## 7. Debuggability and introspection

- Standard pass tracing (“before/after” dumps).
- Type-check diagnostics:
  - layout incompatibility
  - stream protocol mismatches
  - missing backend handlers/capabilities
- Optional execution tracing hooks in bindings.

Current status: **partial**.
- implemented: pass traces, staged artifacts, structured diagnostics, replay,
  semantic diff, minimize, bisect, and explain
- missing: node-aware semantic diff, fully uniform diagnostic payloads, and
  broader future backend/extension debug guidance

---

## 8. Deep dives index

Feature deep dives for the broader target live in:

- `docs/todo/feats/01_extensibility.md`
- `docs/todo/feats/02_dialects_wsp.md`
- `docs/todo/feats/03_dialects_csp.md`
- `docs/todo/feats/04_intrinsics.md`
- `docs/todo/feats/05_layout.md`
- `docs/todo/feats/06_passes_pipelines.md`
- `docs/todo/feats/07_backends_artifacts.md`
- `docs/todo/feats/08_binding_runtime.md`
- `docs/todo/feats/09_debuggability.md`
- `docs/todo/feats/10_agentic_development.md`
