# Retargetable Extensibility for ML Compilers

**Purpose**: a research analysis of what makes an ML compiler truly extensible/retargetable across heterogeneous hardware, why this is difficult in practice (Triton/JAX/TileLang/MLIR ecosystems), and what HTP should do differently to win.

This report is intentionally **concrete**: it uses code-level examples from Triton’s implementation of warp specialization and loop pipelining.

## 0. Executive summary (draft)

A compiler is *retargetable* when a new backend can be added without (a) forking the whole stack, (b) re-deriving semantics from lowered artifacts, or (c) rewriting every optimization. In practice, retargetability requires more than “IR + passes”; it requires **explicit contracts** (capabilities, effects, layout + memory models, and backend artifact contracts) that make compositions checkable.

Triton demonstrates the core tension:

- It is successful because it bakes in a strong GPU execution model (program-ID grid, warps, shared memory, async pipelines).
- It becomes difficult to retarget broadly because high-end performance features (e.g., warp specialization) are **cross-cutting whole-stack features**: new dialect ops + new analysis + new lowering + backend-specific code, plus implicit invariants carried via attributes and pass ordering.

HTP’s opportunity is to:

- make hardware-/backend-specific constraints explicit via **typed capabilities and effects**,
- unify **layout facets** (distribution + memory + hardware placement) so the same “intent” can be lowered differently per backend,
- treat compilation output as a stable **artifact contract** consumed by backends/runtimes,
- and scale extension composition via a **constraint solver** (satisfiable pipelines), rather than relying on implicit MLIR pass ordering.

## 1. Definitions: what we mean by “extensible” and “retargetable”

### 1.1 Extensibility (operational)

An ML compiler is **extensible** if third parties can add each of the following without modifying the core compiler:

- A new programming model / dialect (e.g., CSP vs WSP)
- A new intrinsic set (backend ops) with typed contracts
- A new layout facet or typing rule
- A new analysis / pass
- A new pipeline (pass ordering + output contract)
- A new backend target
- A new binding/runtime integration

“Extensible” is not “has plugin hooks”; it means the extension can be *composed* with other extensions safely and predictably.

### 1.2 Retargetability (operational)

A compiler is **retargetable** if adding a backend does not require:

- forking core IR semantics,
- cloning unrelated optimizations,
- or re-implementing the same scheduling logic in target-specific ad-hoc ways.

In practice, retargetability is about *where semantics live*:

- If semantics are only implicit in a backend lowering, the compiler is not retargetable.
- If semantics are explicit and typed at a stable layer, multiple backends can share the same high-level transforms.

## 2. A retargetability checklist (what must be explicit)

This checklist is used in later sections to evaluate systems.

1) **Execution model contract**
- What is the unit of parallelism (threads/warps/wavefronts/tiles/cores/processes)?
- What is the synchronization model?

2) **Memory model contract**
- What memory spaces exist? (HBM/L2/SMEM/UB/TileMem/etc.)
- What is the async copy model? barriers? events?

3) **Layout contract**
- What does “layout” mean across:
  - distributed sharding/replication,
  - on-device tiling/vectorization,
  - physical memory layout/banking?

4) **Scheduling contract**
- Which scheduling decisions are user-controlled vs compiler-controlled?
- How are those decisions represented (typed directives vs ad-hoc attrs)?

5) **Effect/Protocol contract**
- Are async communication and collectives represented as checkable effects?
- Are deadlock/bounds/protocol mismatches statically catchable?

6) **Optimization contract**
- Can optimizations be expressed against stable abstractions, or do they depend on backend-specific lowered forms?

7) **Backend surface area & stability**
- What must a backend implement?
- Is it stable enough that new backends don’t chase internal refactors?

8) **Artifact contract**
- What is the output package? Is it inspectable/reproducible?
- How does runtime/binding consume it?

## 3. Triton case study: warp specialization is whole-stack

### 3.1 Roadmap claim: autoWS is a pass pipeline that passes decisions via attributes

Primary source:
- https://pytorch.org/blog/warp-specialization-in-triton-design-and-roadmap

The blog describes an autoWS pipeline with (at least) 6–7 conceptual passes (loop scheduler, partition scheduler, memory planner, code partitioner, etc.), and explicitly notes that decisions are often carried via operation attributes.

### 3.2 Concrete code: NV Hopper warp specialization pass + its constraints

Warp specialization is not a single monolithic pass; it is a pipeline of analyses and transforms. Even its *starting point* is NVIDIA-specific:

- Task partitioning relies on `ttng::WarpGroupDotOp` (see `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSTaskPartition.cpp`).
- The transform chooses producer loads by backward-slicing from dot operands and annotates ops with async task IDs that later passes consume.


In `triton-lang/triton`, warp specialization lives under NVIDIA/Hopper code:

- Pass driver: `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization.cpp`
- Core phases: `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSCodePartition.cpp`
- Comm ops: `references/triton/third_party/nvidia/include/Dialect/NVWS/IR/NVWSOps.td`

Key observations from `WarpSpecialization.cpp`:

- The pass triggers only if a loop is tagged with `tt.warp_specialize` and `tt.num_stages > 1`.
- It hard-requires `lookupNumWarps(funcOp) == 4`.
- It currently bails out if there is *any* `scf.if` with an else block (explicit TODO about handling channels in else).
- It performs a small heuristic search over `numWarpGroups` (3 → 2) to find a workable partition.

These are not merely “implementation details”: they are **semantic and control-flow constraints** that arise from the current representation of channels, barriers, and partitioned regions.

### 3.3 Concrete code: code partitioning introduces new comm ops and barrier lowering

In addition to code partitioning itself, Triton must materialize async memory movement into real instruction constraints. For example, NVIDIA `cp.async` lowering enforces hard legality constraints (see `references/triton/third_party/nvidia/lib/TritonNVIDIAGPUToLLVM/LoadStoreOpToLLVM.cpp`):

- rejects transfers smaller than 4 bytes,
- rejects cross-CTA async loads,
- rejects certain non-trivial block-dimension layouts.

This is a key retargetability lesson: “async copy” is not a portable semantic by default; its legality and performance depend on the backend’s instruction set and memory model.


`WSCodePartition.cpp` shows an explicit multi-step pipeline:

- Create buffers per channel
- Insert async copies (and local copies)
- Create tokens/barriers
- Insert communication ops (`ProducerAcquire/Commit/ConsumerWait/Release`)
- Special-case TMA lowering

This produces a *new internal program structure*: outlined partitions guarded by warp-group conditions plus explicit comm ops.

### 3.6 Triton backend pipelines are per-vendor and per-arch

### 3.7 Another concrete example: matmul acceleration is not shared

Even for a seemingly universal operation like matmul/dot, Triton’s legalization and instruction selection differ per vendor:

- AMD implements `tritonamdgpu-accelerate-matmul` with ISA-family-specific rewrite pattern sets (MFMA vs WMMA variants, scaled-blocked decompositions, etc.). See `references/triton/third_party/amd/include/TritonAMDGPUTransforms/Passes.td` and `references/triton/third_party/amd/lib/TritonAMDGPUTransforms/AccelerateAMDMatmul.cpp`.
- NVIDIA uses a different set of passes and lowerings keyed off compute capability (e.g., MMA version selection, WGMMA/TMA integration).

This matters because ‘retargetability’ is not just about having a common op name; it is about having a common *semantic and scheduling contract* that lets backends specialize without duplicating the entire optimization story.

Triton’s Python backends explicitly construct pass pipelines that branch on the target architecture. For example, NVIDIA `make_ttgir` selects different pipelines for SM80/90 vs SM100+ and wires in warp specialization and TMA lowering (see `references/triton/third_party/nvidia/backend/compiler.py`). AMD has a different pipeline controlled by `gfx*` arch and feature knobs like async copy and ping-pong scheduling (see `references/triton/third_party/amd/backend/compiler.py`).

This is not a criticism; it is an empirical observation: *retargetability is bounded by how much of the compiler is allowed to be target-specific*. If high performance depends on deep target-specific scheduling/memory/sync features, a pass-based architecture tends to accumulate per-target pipelines that are difficult to share.

### 3.4 Why this matters for retargetability

Warp specialization is a representative “top-tier optimization feature” because it is not purely algebraic; it depends on:

- a specific hardware concurrency hierarchy (warp groups),
- specific async data movement mechanisms (e.g., TMA),
- and specific barrier/event semantics.

To “retarget warp specialization” to a new backend, you must re-answer:

- What is the equivalent of a warp group (if any)?
- What is the equivalent of TMA loads/stores and their barrier semantics?
- What is the memory space for inter-partition comm (SMEM/TMEM/…)?
- How are these expressed in IR so they can be analyzed/scheduled?

In Triton, these answers are materially encoded in:

- NVWS dialect ops,
- Hopper-specific transforms,
- and cross-cutting lowering utilities.

That implies: adding a new backend with different concurrency/memory models either (a) forks the feature or (b) forces a new shared abstraction layer above NVWS.

## 4. Why “MLIR dialects + passes” is not enough by itself

### 3.5 Lowering abstraction still encodes a GPU execution model

Even outside the Hopper-specific code, Triton’s shared lowering interface (`TargetInfoBase`) is GPU-shaped: it includes warp shuffles, ballots, warp-level barriers, and program-id semantics (see `references/triton/include/triton/Conversion/TritonGPUToLLVM/TargetInfoBase.h`).

This abstraction is excellent for CUDA-vs-ROCm portability, but it highlights a boundary: retargeting to non-GPU hardware (spatial arrays, NPUs with different synchronization, etc.) likely requires new semantic interfaces, not just implementing one more TargetInfo subclass.


This section does **not** claim “MLIR is bad”. It claims:

> MLIR’s mechanisms (dialects, pattern rewrites, passes) do not automatically provide *composition correctness* or *retargetable semantics*.

### 4.1 The failure mode: implicit invariants + attribute spaghetti

A pass pipeline becomes fragile when:

- pass A expects certain attributes to exist and be consistent,
- pass B rewrites CFG in a way that invalidates pass A’s assumptions,
- analyses and lowerings must special-case “if warp-specialized” vs “if SWP” vs “if backend == …”,
- and there is no typed contract system enforcing these dependencies.

Triton’s warp specialization is a concrete example: it is gated on `numWarps == 4`, loop attributes, and control-flow limitations, and it interacts with other transforms (loop pipelining, MMA lowering).

### 4.2 Dialect composition does not solve hardware semantic mismatch

Even if you create a dialect per backend, you still need:

- a stable semantic layer above them to share optimizations,
- or you accept that every backend duplicates a large pass pipeline.

For heterogeneous targets (GPU vs NPU vs AIE), the semantic mismatch is not cosmetic; it is fundamental:

- different memory spaces and async primitives,
- different parallel execution granularities,
- different scheduling levers,
- different legal transformations.

Without explicit contracts, a pass-based system tends to devolve into:

- backend-specific lowerings everywhere,
- and “retargeting” becomes a rewrite.

## 4.3 LittleKernel viewpoint: emitter-first retargeting (and its limits)

The LittleKernel note (`references/size-littlekernel.md`) argues for a lightweight approach: use Python AST as the IR, minimize passes (const-fold, inline, type inference), and treat hardware-specific features as hot-pluggable intrinsics whose codegen is handled by an emitter. The author’s retargeting claim is essentially: “hardware is fragmented; swapping hardware should only require swapping the emitter and registering new intrinsics.”

This viewpoint captures an important truth: for many SOTA kernels, the *dominant complexity is hardware-specific scheduling and instruction use* (e.g., NVIDIA WGMMA/TMA vs other vendors’ tensor cores). A heavy compiler that hides those details can become a bottleneck.

However, for a *multi-backend compiler framework* (HTP’s goal), “swap the emitter” is not sufficient on its own:

- Different targets have different memory and synchronization semantics; without explicit contracts, an emitter can silently generate incorrect code.
- Composition (kernel → megakernel → serving routine) requires checkable protocols (bounded channels, collectives, barriers).
- Even if passes are few, the remaining passes must enforce strong typing/effects/layout legality, or retargeting degenerates into debugging backend-specific failures.

HTP can adopt the *good part* of this view (AST-first extensibility, hot-pluggable intrinsics, emitter-as-a-first-class component) while adding what the lightweight approach omits: capability/effect/layout contracts that make compositions and retargeting diagnosable and safe.

## 5. What HTP should do differently (and why it might win)

HTP’s differentiators should be expressed as mechanisms:

1) **Capability-typed pipelines**
- Every dialect/intrinsic/pass/backend declares `requires/provides`.
- Pipeline selection is satisfiability checked (and diagnosable).

2) **Unified layout + effect system**
- Layout has facets: distribution + memory + hardware placement.
- Async communication and collectives are checkable effects.

3) **Hardware model as data**
- Backends target an explicit `ArchModel` (hierarchy + memory spaces + async primitives).
- Intrinsics and schedules declare what they require of the `ArchModel`.

4) **Artifact contracts as the integration boundary**
- Compilation emits a stable package (manifest + dumps + codegen outputs).
- Bindings consume the package; runtime integration is explicit and testable.

5) **AST-first extensibility + optional islands**
- Python AST match/apply is the default extension surface.
- MLIR “islands” are used only where they add leverage (e.g., AIE), and their entry/exit contracts are explicit.

### 5.1 Recasting Triton’s warp specialization in HTP terms

An HTP version of “warp specialization” should be modeled as:

- a *generic* program partitioning transformation that introduces a typed async channel effect,
- parameterized by a hardware capability like `SubgroupPartitioning` + `AsyncCopy` + `Barrier`.

Then:

- on NVIDIA, `SubgroupPartitioning` maps to warp groups and NV-specific barriers/TMA,
- on other targets, the pass either selects a different partitioning strategy or rejects with a precise capability mismatch.

This avoids “bail out silently because numWarps != 4” and replaces it with a capability/type error.

## 6. JAX/XLA and TileLang comparisons

This section is not meant to “rank” systems; it is meant to clarify *where* each system sits on the retargetability checklist and why HTP’s target differs.

### 6.1 JAX/XLA/StableHLO: portable tensor algebra, limited low-level extensibility

JAX’s core portability story flows through XLA’s high-level IR (StableHLO / HLO). This is a strong kind of retargetability:

- If your program stays within the HLO abstraction, new devices can be supported by adding/maintaining an XLA backend and runtime (typically via PJRT).
- Whole-program graph optimizations (fusion, algebraic simplification, layout assignment) are expressed at a relatively stable level.

But the flip side is also structural:

- HLO is intentionally **not** a kernel ISA; it does not directly express target-specific async copy/barrier protocols, warp-group partitioning, or tensor-core instruction contracts.
- When performance depends on low-level mechanisms, the system tends to use:
  - backend-specific emitters (e.g., XLA:GPU’s Triton emitter path),
  - vendor libraries,
  - or custom calls.

So the “extensibility” boundary is higher: adding a new low-level primitive often means extending backend codegen or introducing custom-call hooks rather than writing user-level schedule/program transformations.

Reference: OpenXLA XLA:GPU architecture overview (StableHLO → XLA → backend codegen; native and Triton-based emitters; PJRT runtime).
- https://openxla.org/xla/gpu_architecture

### 6.2 TileLang: kernel DSL with explicit schedule knobs (Triton-adjacent)

TileLang positions as a Python kernel DSL with explicit scheduling constructs (grid/thread mapping, shared allocations, pipelined loops, swizzles, etc.). This is closer to Triton than to XLA:

- You get fine-grained control over kernel structure and memory usage.
- Retargetability across GPU vendors is plausible *within the GPU family* if the DSL’s semantics are carefully chosen.

However, the same core challenge appears:

- Once the DSL exposes hardware-specific concepts (warp-level behavior, shared-memory swizzles, special matrix instructions), the compiler must carry target-specific legality/performance rules.
- Supporting *non-GPU* targets (NPU/AIE) requires either a new semantic layer above these concepts or a different set of primitives.

Reference: TileLang README and examples.
- https://github.com/tile-ai/tilelang

### 6.3 HTP’s intended niche relative to these systems

HTP aims to sit in a different place:

- Like Triton/TileLang, it must support hardware-specific low-level control where needed.
- Like XLA, it must support composition and multi-component programs (kernels → pipelines → serving routines) and multiple backends.

The differentiator HTP needs is **contract-first retargetability**:

- Users (or extensions) can express low-level intent via typed intrinsics and schedule directives.
- The compiler checks capability/effect/layout contracts before lowering.
- Backends provide explicit `ArchModel` capability sets and lowering implementations.

This is how HTP can adopt the best parts of “kernel DSL” systems without becoming a pile of per-target pass pipelines.


## Appendix A: Code pointers (Triton)

- Warp specialization driver: `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization.cpp`
- Code partition steps + comm ops insertion: `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSCodePartition.cpp`
- NVWS dialect ops: `references/triton/third_party/nvidia/include/Dialect/NVWS/IR/NVWSOps.td`
- Pipelining utility attribute keys: `references/triton/include/triton/Dialect/TritonGPU/Transforms/PipeliningUtility.h`
- Loop pipelining latency assignment: `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/AssignLatencies.cpp`
- Python driver stage pipeline: `references/triton/python/triton/compiler/compiler.py`
