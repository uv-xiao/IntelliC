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

### 0.1 Coverage vs the original prompt (audit checklist)

This report was written to satisfy the original research prompt. Mapping:

- “Key to real extensibility / retargetability across hardware”: Sections **1–2** (definitions + checklist).
- “What makes HTP special vs Triton/JAX/TileLang”: Sections **5–6** (mechanisms + comparisons).
- “Why MLIR’s IR+pass mechanism will fail (for heterogeneous retargeting)”: Section **4** (implicit invariants, attrs-as-APIs, pass ordering brittleness, dialect mismatch).
- “Consider Triton’s warp specialization roadmap”: **3.1** (roadmap summary) + **3.3** (roadmap-to-code mapping table).
- “Thorough Triton code exploration with concrete optimization examples”: Section **3** + Appendix **A** (pass pipeline + key files).
- “Consider the LittleKernel (emitter-first) viewpoint from Zhihu”: **4.6** (benefits + what it misses) and how HTP combines the good part with missing contracts.

Known limitations (explicit, not hidden):

- Two “whole-stack” optimizations are reconstructed end-to-end (warp specialization and software pipelining). Other
  optimizations are referenced but not walked with equal depth.
- JAX/XLA and TileLang sections include concrete pointers and mechanics, but not the same “pass-by-pass” reconstruction as Triton’s autoWS pipeline.

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

Warp specialization is not a single “toggle”; in Triton it is a **whole-stack feature** that exists in multiple
implementations depending on NVIDIA architecture generation.

Triton’s NVIDIA backend makes this explicit (see `references/triton/third_party/nvidia/backend/compiler.py`):
- SM80/SM90 (capability // 10 ∈ {8, 9}): uses a Hopper-specific pipeline via `nvidia.passes.hopper.add_hopper_warpspec(...)`.
- SM100+ (capability // 10 ≥ 10): uses `passes.ttgpuir.add_warp_specialize(...)` followed by
  `passes.ttgpuir.add_optimize_partition_warps(...)`.

#### 3.2.1 Hopper path: NVIDIA/Hopper warp specialization driver + constraints

In the SM80/SM90 path, warp specialization lives under NVIDIA/Hopper code:

- Task partitioning relies on `ttng::WarpGroupDotOp` (see `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSTaskPartition.cpp`).
- The transform chooses producer loads by backward-slicing from dot operands and annotates ops with async task IDs that later passes consume.

- Pass driver: `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization.cpp`
- Core phases: `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSCodePartition.cpp`
- Comm ops: `references/triton/third_party/nvidia/include/Dialect/NVWS/IR/NVWSOps.td`

Key observations from `WarpSpecialization.cpp`:

- The pass triggers only if a loop is tagged with `tt.warp_specialize` and `tt.num_stages > 1`.
- It hard-requires `lookupNumWarps(funcOp) == 4`.
- It currently bails out if there is *any* `scf.if` with an else block (explicit TODO about handling channels in else).
- It performs a small heuristic search over `numWarpGroups` (3 → 2) to find a workable partition.

These are not merely “implementation details”: they are **semantic and control-flow constraints** that arise from the current representation of channels, barriers, and partitioned regions.

#### 3.2.2 Non-portable semantics example: `cp.async` legality is instruction-level

Even outside warp specialization, Triton illustrates a general retargetability constraint: “async copy” is only portable
if you define its *legality* and *effects* as a contract.

For example, NVIDIA `cp.async` lowering enforces hard legality constraints (see `references/triton/third_party/nvidia/lib/TritonNVIDIAGPUToLLVM/LoadStoreOpToLLVM.cpp`):

- rejects transfers smaller than 4 bytes,
- rejects cross-CTA async loads,
- rejects certain non-trivial block-dimension layouts.

This is a key retargetability lesson: “async copy” is not a portable semantic by default; its legality and performance depend on the backend’s instruction set and memory model.

### 3.3 SM100+ path: upstream “automatic warp specialization” is an explicit pass pipeline

On SM100+, Triton builds warp specialization using a coordinated pipeline in
`references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/AutomaticWarpSpecialization.cpp`:

- `tritongpu-partition-scheduling` (`PartitionScheduling.cpp`)
- `nvws-hoist-tmem-store`
- `nvws-insert-aref`
- `nvws-insert-tmem-aref`
- cleanup: `SCCP` + `CSE`
- `nvws-lower-aref` (option: `numStages`)
- `tritongpu-partition-loops` (`PartitionLoops.cpp`)
- `nvws-lower-warp-group` (convert `nvws.warp_group` → `ttg.warp_specialize`)
- `tritongpu-schedule-loops` (loop scheduling/pipelining)

Roadmap-to-code mapping (approximate):

| Roadmap concept | Concrete pass(es) | What it materially introduces |
|---|---|---|
| Partition scheduling | `tritongpu-partition-scheduling` | `ttg.partition` / `ttg.partition_outputs` / `ttg.partition_stages` attrs that later passes consume |
| Memory/sync planning | `nvws-insert-aref`, `nvws-insert-tmem-aref` | `nvws.aref.*` protocol ops bridging producer↔consumer partitions |
| Barrier/event lowering | `nvws-lower-aref` | NVIDIA barrier ops (`ttng.*barrier*`) + derived wait/signal placement from use-def chains |
| Code partitioning / outlining | `tritongpu-partition-loops` | region cloning, shared-memory plumbing for cross-partition results, `nvws.warp_group` structure |
| Warp-specialize IR formation | `nvws-lower-warp-group` | `ttg.warp_specialize` (partition regions + warp counts) |
| Loop scheduling | `tritongpu-schedule-loops` | SWP decisions integrated with warp-specialize structure |
| Peephole cleanup | `SCCP`, `CSE` | canonical cleanup to keep arithmetic/control-flow sane post-rewrites |
| Extra optimization | `nvws-hoist-tmem-store` | avoids extra cross-partition TMEM ownership transfers in some nested-loop cases |

After the MLIR pass pipeline, it additionally runs `multiBufferTMADescriptors(...)` to multi-buffer and lower TMA
descriptors outside SWP so nested-loop descriptor updates remain correct.

The important observation is not “this is many passes”; it is that:
- the pipeline is **cross-cutting** (partitioning ↔ sync protocol ↔ lowering ↔ scheduling),
- and it relies on **decisions carried via attributes** as the contract between those passes.

### 3.4 Partition scheduling: heuristics → serialized attributes (the hidden contract)

`tritongpu-partition-scheduling` (`references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/PartitionScheduling.cpp`) builds a
dataflow graph, assigns partitions using heuristics, then **serializes** the result into attributes that downstream
passes rely on:

- per-op partition membership via `ttg.partition` (see `kPartitionAttrName`)
- per-structured-op outputs via `ttg.partition_outputs` (see `kPartitionOutputsAttrName`)
- per-loop partition stage info via `ttg.partition_stages` (see `kPartitionStagesAttrName`)

This is precisely the “decisions passed via attrs” pattern described in the roadmap.

### 3.5 Partition loops: outlining + shared-memory plumbing becomes IR structure

`tritongpu-partition-loops` (`references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/PartitionLoops.cpp`) consumes those
attributes and turns a loop into a partitioned structure:

- clones ops into per-partition regions,
- allocates shared-memory buffers for tensor results computed by non-default partitions,
- introduces `nvws.warp_group` with partition regions and yields, then relies on NVWS lowering to produce `ttg.warp_specialize`.

NVWS pass docs (`references/triton/third_party/nvidia/include/Dialect/NVWS/Transforms/Passes.td`) show the intended semantics:
- `nvws-insert-aref`: inserts `nvws.aref.*` ops to automate producer↔consumer synchronization between partitions.
- `nvws-lower-aref`: lowers arefs into `ttng.*barrier*` ops and derives wait/signal placement from use-def chains.
- `nvws-lower-warp-group`: converts `nvws.warp_group` to `ttg.warp_specialize`.

### 3.6 Walkthrough: implementing cross-partition sync via `nvws.aref` (why it’s hard to retarget)

This walkthrough focuses on one concrete “optimization feature” that is easy to describe at a high level (“make producer
and consumer partitions run concurrently, with correct synchronization”), but becomes hard to retarget because it spans:

- partition analysis + scheduling,
- explicit sync protocol introduction,
- multi-buffering/staging for pipelined loops,
- and lowering to target-specific barrier instructions.

#### 3.6.1 Preconditions (what the pipeline assumes is already true)

The `nvws.aref` pipeline assumes:

- The loop is already selected for warp specialization (`tt.warp_specialize` on a loop) and has a staged pipeline
  (`tt.num_stages` / SWP expectations).
- Partition membership and stage decisions already exist as attributes produced by `tritongpu-partition-scheduling`
  (`ttg.partition`, `ttg.partition_outputs`, `ttg.partition_stages`).

In other words: the correctness of `nvws.aref` depends on earlier passes producing a consistent “attrs contract”.

#### 3.6.2 Protocol introduction: `nvws-insert-aref`

Pass implementation: `references/triton/third_party/nvidia/lib/Dialect/NVWS/Transforms/InsertAref.cpp`.

At a high level, `nvws-insert-aref` walks warp-specialized loops and inserts `nvws.aref.*` operations on values that
cross producer/consumer partition boundaries:

1) **Find candidate loops**
   - It selects `scf.for` loops with `triton::kWarpSpecializeAttrName` and an existing partition annotation (see
     `runOnFunction` in `NVWSArefInsertion`).

2) **Handle structured control-flow and loop-carried values**
   - It explicitly considers `iter_args` and loop-carried values because “producer in iteration i” may feed “consumer in
     iteration i-1”, or the init value. This forces protocol insertion to reason about *iteration distance*, not just
     SSA dominance.

3) **Process produced values and their uses by partition**
   - For each “produced value”, it groups uses by the consumer partition IDs (derived from the partition attrs contract),
     and creates an aref when the use partition set is not a subset of the producer partition set.

4) **Create an aref at the outer warp-specialized loop**
   - It creates `nvws.aref.create` at the outer WS loop (via `getOuterWSLoop(loop)` and `createAref(...)`), so the aref
     buffer lifetime spans the whole specialized loop.

5) **Wrap the producer side**
   - It inserts an `ArefPutEnterOp`/`ArefPutExitOp` (or descriptor-load-specific NVWS ops) around the producer operation to
     materialize “produce into an aref-owned SMEM buffer”.

6) **Wrap the consumer side at a carefully chosen insertion point**
   - It inserts `ArefGetEnterOp` at the earliest user in the block (see `getEarliestUserInBlock(...)`) and pairs it with an
     `ArefGetExitOp` after a post-dominant consumer to model the “consumer region” in which the value is “borrowed”.

7) **Erase stale ops**
   - It deletes “stale” producer/consumer ops that have been replaced by aref operations.

The key point: this is not just a local rewrite; it is a *protocol construction* pass that depends on partition analysis,
control-flow structure, and lifetime/placement decisions.

#### 3.6.3 Protocol lowering: `nvws-lower-aref` → NVIDIA barrier ops

Pass implementation: `references/triton/third_party/nvidia/lib/Dialect/NVWS/Transforms/LowerAref.cpp`.

`nvws-lower-aref` takes the IR with aref protocol ops and lowers it into a concrete synchronization implementation:

1) **Combine and normalize arefs**
   - It combines compatible arefs inside warp-specialized loops (`combineArefs(loop)`), reducing protocol overhead.

2) **Multi-buffer arefs for pipelined execution**
   - For arefs whose producers are global→shared loads (`isProducerLoad(arefOp)`), it runs `multiBufferAref(arefOps, numStages)`
     so producer/consumer can overlap across pipeline stages.

3) **Assign stage/phase metadata**
   - It runs `nvws-assign-stage-phase`, which annotates aref ops with buffer stage/phase decisions.

4) **Lower aref creation/usage into barrier instructions**
   - A rewrite pattern (`LowerArefCreate`) converts aref ops into `ttng.*barrier*` ops and places waits/signals based on the
     use-def chains and empty/full semantics described in the NVWS pass docs
     (`references/triton/third_party/nvidia/include/Dialect/NVWS/Transforms/Passes.td`).

This is where “portable async handoff” becomes “target-specific barrier ISA”.

#### 3.6.4 What retargeting this would actually require

To support an additional target with a different execution/memory/sync model, you would need to provide equivalents for:

- **A semantic protocol op set** (aref-like) that can express buffered handoff + empty/full state across partitions.
- **A staged execution model** compatible with loop pipelining (multi-buffering, stage/phase assignment).
- **A lowering target dialect** that has the right barrier/event primitives (and a memory model they are correct under).

For AMD GPUs:
- The hardware synchronization and async copy mechanisms are different (wavefront model, LDS semantics, and different
  instruction/legalization constraints). A faithful port is not “implement the same passes”; it is “redefine the protocol
  semantics and re-lower them into ROCm/AMDGPU primitives”.

For NPUs/AIE/spatial targets:
- The equivalent of “barrier + shared memory handoff” may be DMA engines + events, explicit queues, or ping-pong SRAM.
  Retargeting needs a target-neutral protocol contract above the ISA-level details.

This is the core extensibility lesson for HTP: if the protocol semantics only exist as NVIDIA-specific dialects and
passes, a new backend cannot reuse them. HTP needs a **contract-first** representation of protocols/effects (buffered
handoff, async copy, barrier/event) that can be lowered differently per target.

### 3.7 `optimize_partition_warps`: re-entering the compiler pipeline per partition

The SM100+ path also runs `tritongpu-optimize-partition-warps`
(`references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/OptimizePartitionWarps.cpp`), which:

- extracts each `ttg.warp_specialize` partition body into a temporary `tt.func` in a synthetic module,
- clears tensor encodings, then re-runs `convert-triton-to-tritongpu` + `relayout` under a new `num_warps`,
- then re-injects the transformed region back.

This is a powerful technique, but it expands the “retargetability surface area”: it assumes that the pipeline is safe to
re-enter on extracted regions, that the target has compatible layout assignment semantics, and that the relevant analyses
(e.g., axis info) exist for the target dialect set.

### 3.8 Backend pipelines are per-vendor and per-arch (and why that matters)

Even for a seemingly universal operation like matmul/dot, Triton’s legalization and instruction selection differ per vendor:

- AMD implements `tritonamdgpu-accelerate-matmul` with ISA-family-specific rewrite pattern sets (MFMA vs WMMA variants, scaled-blocked decompositions, etc.). See `references/triton/third_party/amd/include/TritonAMDGPUTransforms/Passes.td` and `references/triton/third_party/amd/lib/TritonAMDGPUTransforms/AccelerateAMDMatmul.cpp`.
- NVIDIA uses a different set of passes and lowerings keyed off compute capability (e.g., MMA version selection, WGMMA/TMA integration).

This matters because ‘retargetability’ is not just about having a common op name; it is about having a common *semantic and scheduling contract* that lets backends specialize without duplicating the entire optimization story.

Triton’s Python backends explicitly construct pass pipelines that branch on the target architecture. For example, NVIDIA `make_ttgir` selects different pipelines for SM80/90 vs SM100+ and wires in warp specialization and TMA lowering (see `references/triton/third_party/nvidia/backend/compiler.py`). AMD has a different pipeline controlled by `gfx*` arch and feature knobs like async copy and ping-pong scheduling (see `references/triton/third_party/amd/backend/compiler.py`).

This is not a criticism; it is an empirical observation: *retargetability is bounded by how much of the compiler is allowed to be target-specific*. If high performance depends on deep target-specific scheduling/memory/sync features, a pass-based architecture tends to accumulate per-target pipelines that are difficult to share.

### 3.9 Why this matters for retargetability

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

### 3.10 Software pipelining + async loads/stores is also whole-stack (and is not “portable by default”)

Warp specialization is not the only cross-cutting feature in Triton. Software pipelining (SWP) and async data movement
is a second representative case study because it mixes:

- target-specific async primitives (`cp.async`, TMA load/store, fence semantics),
- loop scheduling heuristics, and
- multi-buffering / descriptor update logic that interacts with control flow.

The key observation is the same as warp specialization: it is not a single pass or a single op; it is a coordinated
pipeline with implicit contracts.

#### 3.10.1 Where SWP shows up in Triton’s backend pipelines (concrete pass ordering)

On NVIDIA, the CUDA backend wires SWP explicitly:

- `passes.ttgpuir.add_assign_latencies(pm, opt.num_stages)`
- `passes.ttgpuir.add_schedule_loops(pm)`
- `passes.ttgpuir.add_pipeline(pm, opt.num_stages, dump_enabled)`

in architecture-dependent branches (SM80/90 path and SM100+ path). See:
`references/triton/third_party/nvidia/backend/compiler.py` (`make_ttgir`).

On AMD, the HIP backend uses a different SWP surface with explicit feature flags:

- `amd.passes.ttgpuir.add_schedule_loops(pm, options.num_stages)`
- `amd.passes.ttgpuir.add_pipeline(pm, use_async_copy, use_block_pingpong)`
- plus additional pipeline-related transforms such as `add_move_up_prologue_loads` and optional
  `add_block_pingpong(pm, options.num_stages)`.

See `references/triton/third_party/amd/backend/compiler.py` (`make_ttgir`).

This already shows a “retargetability fact”: even within “MLIR passes”, the pipeline itself is per-vendor and is
parameterized by target feature knobs.

#### 3.10.2 The hidden contract surface: `tt.num_stages` and stage/cluster attributes

The SWP mechanism relies on an attribute-driven contract that is not a typed semantic layer:

- `tt.num_stages` controls whether/where loops are pipelined.
- scheduling results are represented via attributes such as `loop.stage`, `loop.cluster`,
  `tt.scheduled_max_stage` (and other internal attributes used by the schedule serialization).

These attribute names are defined in `references/triton/include/triton/Dialect/TritonGPU/Transforms/PipeliningUtility.h`.

This is the same “attrs as APIs” pattern as warp specialization: phases communicate through attributes rather than a
checkable contract system.

#### 3.10.3 Latency assignment is target-conditional and bakes in legality constraints

`tritongpu-assign-latencies` is not merely “a heuristic”; it bakes in target-specific async legality constraints and
structures the pipeline’s scheduling space:

- It skips loops that are not supported by the current expander (`distance > 1`, “outer loops”).
  See `preCondition(...)` in `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/AssignLatencies.cpp`.
- It decides whether “pipelining without dot” is enabled based on loop attributes (checks for `tt.num_stages`).
- It filters “small loads” as non-beneficial for pipelining based on async legality:
  - `canBeConvertedToAsyncLoad(...)` computes an effective width from AxisInfo contiguity/mask alignment and requires
    `width >= 32` bits (comment references `cp.async` cp-size constraints and register pressure concerns).
    See `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/PipeliningUtility.cpp` and
    `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/AssignLatencies.cpp`.
- It contains special casing for NVIDIA MMAv5 pipelining and multibuffering of accumulators, with explicit hacks around
  `scf.if` placement and warp-specialized loops (`isWarpSpecialized(forOp)` affects latency choices).
  See `AssignMMALatencies` in `AssignLatencies.cpp`.

Retargetability implication: to “share SWP” across targets, you must share (or re-implement) the legality and latency
model of async ops and dot pipelines, not only the pass skeleton.

#### 3.10.4 Loop scheduling encodes subtle semantic exclusions

`tritongpu-schedule-loops` excludes loops that contain:

- `ttg::BarrierOp`, `tt::AssertOp`, or `tt::PrintOp`, and
- distance > 1 dependencies, outer loops.

See `isSafeToPipeline(...)` in
`references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/ScheduleLoops.cpp`.

It also moves certain control-flow (`scf.if`) into an “epilogue cluster” to avoid conflicts with the pipeline schedule.
This is not just optimization; it is a semantic constraint driven by how predication and async operations interact.

#### 3.10.5 The pipeline pass is not “just a transform”: it is a multi-phase compiler subsystem

The `tritongpu-pipeline` pass itself (see `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/SoftwarePipeliner.cpp`)
does multiple phases:

1) `lowerLoops(moduleOp)` introduces async operations and prepares the IR for expansion.
2) `expandLoops(moduleOp)` mechanically expands the loop using `pipelineForLoop(...)` from `PipelineExpander.h`.
   - `PipelineExpander.h` explicitly states it is a **fork** of upstream pipeline transformation, indicating the need for
     custom semantics/stability beyond “generic MLIR SWP”.
3) It cleans up pipelining attributes (`removePipeliningAttributes(moduleOp)`).
4) It performs post-processing with NVIDIA-specific details:
   - `pipelineWgmma(...)` (launch dots for WGMMA pipelining),
   - `updateWaits(...)` (schedule waits),
   - and additional per-loop lowering `pipelineTMAStores(forOp)` for loops with `num_stage > 1`.

This is a second “whole-stack” observation: SWP is a subsystem that mixes generic MLIR mechanics with target-specific
post-processing.

#### 3.10.6 Concrete example: pipelining TMA stores requires descriptor multibuffering and fence protocol

TMA store pipelining (`pipelineTMAStores`) illustrates how “async store” is a protocol, not a single op.

The transform (see `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/TMAStoresPipeline.cpp`) does:

- Identify `tt::DescriptorStoreLikeOpInterface` ops inside the loop.
- Allocate shared memory buffers (`ttg::LocalAllocOp`) with encoding derived from the tensor descriptor
  (`getEncodingFromDescriptor(...)`).
- Rewrite the store into an async protocol sequence:
  - `ttng::TMAStoreWaitOp(0)` (place wait before store)
  - `ttg::LocalStoreOp(src, alloc)`
  - `ttng::FenceAsyncSharedOp`
  - one of:
    - `ttng::AsyncTMACopyLocalToGlobalOp`
    - `ttng::AsyncTMAReduceOp`
    - `ttng::AsyncTMAScatterOp`
- Deallocate buffers after the loop, guarded by a final `TMAStoreWaitOp(0)`.

Critically, if the loop uses *device-side* TMA descriptors, it performs descriptor multibuffering by calling
`lowerTMADescriptors(...)`.

`lowerTMADescriptors` (in `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/PipeliningUtility.cpp`) is a
non-trivial control-flow-aware rewrite:

- allocate per-descriptor “buffer slices” in global scratch memory (`GlobalScratchAllocOp`) sized by
  `maxStage * ttng::TMA_SIZE_BYTES`,
- add iter-arg counters to the loop (one counter per descriptor) to rotate buffer slices,
- rewrite descriptor creation (`tt::MakeTensorDescOp`) into writes into the selected slice using `ttng::createTMADesc(...)`
  and a fence-proxy acquire (`TensormapFenceproxyAcquireOp`),
- and propagate counter updates out of nested `scf.if` regions via `sinkValueRedefinition(...)` before updating the loop
  yield.

This is a concrete, code-level example of why retargeting async pipelines is hard: the “descriptor update protocol” is
deeply tied to the target ISA and its memory/fence semantics, and it requires dedicated compiler logic beyond generic
pattern rewrites.

#### 3.10.7 What retargeting SWP/async actually requires

To retarget this optimization to a new backend (or a non-GPU target), you must define and implement:

- an async copy/store contract (legality: minimum transfer size, alignment, memory space; effects: commit/wait semantics),
- a barrier/event/fence contract (visibility guarantees across producer/consumer),
- multi-buffering rules (how buffers/descriptor slices are allocated and rotated),
- and control-flow interaction rules (what happens with `scf.if` / predication in prologue/epilogue).

Without these explicit contracts, an “IR + passes” approach tends to:

- bake legality and protocol assumptions into ad-hoc pass code,
- communicate via implicit attributes,
- and require per-target pipeline forks (which is exactly what we observe in Triton’s NV vs AMD backends).

This is precisely where HTP’s “typed effects + capability-typed pipelines + artifact contracts” can win: it can force the
async protocol and its discharge rules to be explicit and checkable, and let backends implement only the capability
handlers they support (or fail with a precise unsatisfied-constraint explanation).

## 4. Why “MLIR dialects + passes” is not enough by itself

### 4.1 Lowering abstraction still encodes a GPU execution model

Even outside the Hopper-specific code, Triton’s shared lowering interface (`TargetInfoBase`) is GPU-shaped: it includes warp shuffles, ballots, warp-level barriers, and program-id semantics (see `references/triton/include/triton/Conversion/TritonGPUToLLVM/TargetInfoBase.h`).

This abstraction is excellent for CUDA-vs-ROCm portability, but it highlights a boundary: retargeting to non-GPU hardware (spatial arrays, NPUs with different synchronization, etc.) likely requires new semantic interfaces, not just implementing one more TargetInfo subclass.


This section does **not** claim “MLIR is bad”. It claims:

> MLIR’s mechanisms (dialects, pattern rewrites, passes) do not automatically provide *composition correctness* or *retargetable semantics*.

### 4.2 The failure mode: implicit invariants + attribute contracts (“attrs as APIs”)

A pass pipeline becomes fragile when:

- pass A expects certain attributes to exist and be consistent,
- pass B rewrites CFG in a way that invalidates pass A’s assumptions,
- analyses and lowerings must special-case “if warp-specialized” vs “if SWP” vs “if backend == …”,
- and there is no typed contract system enforcing these dependencies.

Triton’s warp specialization is a concrete example, and it makes the dependency chain visible:

- `tritongpu-partition-scheduling` computes a graph partitioning, then **serializes** the result to attrs such as
  `ttg.partition`, `ttg.partition_outputs`, `ttg.partition_stages`
  (`references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/PartitionScheduling.cpp`).
- `nvws-insert-aref` *assumes those attrs exist* (`hasPartition(loop)` and partition outputs) and uses them to decide where
  to insert `nvws.aref.*` protocol ops (`references/triton/third_party/nvidia/lib/Dialect/NVWS/Transforms/InsertAref.cpp`).
- `nvws-lower-aref` assumes the `nvws.aref.*` protocol exists and lowers it to NVIDIA barrier ops (`ttng.*barrier*`) with
  multi-buffering driven by `numStages`
  (`references/triton/third_party/nvidia/lib/Dialect/NVWS/Transforms/LowerAref.cpp`).
- `tritongpu-partition-loops` assumes partition stages exist (it collects loops with `kPartitionStagesAttrName`) and turns
  the loop into a structured partitioned region program (`references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/PartitionLoops.cpp`).

None of these “attrs as APIs” are inherently wrong; they’re practical. The failure mode is that:
- the contracts are *conventional*, not typed/checked at composition boundaries,
- and a third-party extension must learn and preserve them to avoid subtle miscompilations.

### 4.3 Pass ordering brittleness: phase coupling is not self-describing

The SM100+ autoWS entrypoint is literally a hand-authored ordering:
`PartitionScheduling → InsertAref → LowerAref → PartitionLoops → LowerWarpGroup → ScheduleLoops (+ cleanup passes)`.
See `references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/AutomaticWarpSpecialization.cpp`.

This illustrates a common “IR+passes” scaling problem:

- The “correct” ordering is an emergent property of many interacting assumptions (what IR shape each pass expects).
- Adding a new optimization (e.g., another hoist/rewire, another legalization, another peephole) often requires inserting it
  at *exactly* the right phase, or it breaks an implicit invariant for a later pass.
- Pass ordering becomes target-conditional (as in `references/triton/third_party/nvidia/backend/compiler.py`), which makes
  extension composition harder: a plugin pass must know “where” it belongs for each target and feature set.

MLIR provides the *mechanism* to run passes, but it does not provide a first-class concept of:
- “this pass requires effect X / provides effect Y”,
- “this pass refines layout facet L from abstract → concrete”,
- “this pass introduces protocol P with these safety obligations”.

Without those contracts, a pass pipeline remains difficult to retarget and difficult to extend safely.

### 4.4 Re-entrancy and scope: some transforms require re-running sub-pipelines

`tritongpu-optimize-partition-warps` is an example of a transform that can’t be expressed as a simple local rewrite: it
extracts each `ttg.warp_specialize` partition region into a temporary module and re-runs layout assignment passes under a
new warp count (`references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/OptimizePartitionWarps.cpp`).

This creates additional implicit requirements on “the compiler construction model”:

- passes must be safe to re-run on extracted subprograms,
- target metadata must be forwarded correctly (module attrs like target, threads/warp, CTAs),
- layout assignment must be stable and available at the right abstraction level.

For a new target, it is not enough to “add a lowering”; you may need to implement compatible analyses, layout assignment,
and re-entrant sub-pipelines to support such transforms.

### 4.5 Dialect composition does not solve hardware semantic mismatch

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

### 4.6 LittleKernel viewpoint: emitter-first retargeting (and its limits)

The LittleKernel viewpoint (see `docs/reference/littlekernel_emitter_first.md`, originally from https://zhuanlan.zhihu.com/p/2005441887369192285) argues for a lightweight approach: use Python AST as the IR, minimize passes (const-fold, inline, type inference), and treat hardware-specific features as hot-pluggable intrinsics whose codegen is handled by an emitter. The retargeting claim is essentially: “hardware is fragmented; swapping hardware should only require swapping the emitter and registering new intrinsics.”

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

### 5.1 Recasting Triton’s warp specialization (and `nvws.aref`) in HTP terms

Triton’s evidence suggests that “retargetable extensibility” requires **making cross-cutting semantics explicit** before
you get deep into backend-specific dialects/ISAs.

An HTP version of warp specialization should be modeled as:

- a *generic partitioning transform* (split a loop/body into concurrent partitions),
- plus a *typed protocol/effect layer* for partition handoff (“buffered handoff”, “empty/full”, “stage/phase”),
- parameterized by declared hardware capabilities (not by hard-coded invariants like `numWarps == 4`).

Concretely, the ingredients look like:

1) **Capabilities (what hardware/backends declare)**
   - `SubgroupPartitioning` (e.g., warp groups, wave groups, core groups, or “not supported”)
   - `AsyncCopy(kind=cp_async|tma|dma|...)`
   - `BarrierOrEvent(kind=barrier|event|queue|...)`
   - `OnChipMemory(space=smem|lds|sram|...)`

2) **Effects / protocols (what programs introduce and must type-check)**
   - `BufferedHandoff[T, space, stages]` as a first-class effect/protocol with operations like:
     - `handoff.put(value)`, `handoff.get()`, and explicit stage/phase transitions
   - This is the target-neutral analogue of Triton’s `nvws.aref.*` + “lower to barrier ISA” stack.

3) **Layout facets (what gets carried through the pipeline)**
   - `Layout = DistributionFacet ⊗ MemoryFacet ⊗ PlacementFacet`
   - Warp specialization changes *placement* and often forces specific on-chip memory and staging choices; this must be
     represented as a refinement, not as ad-hoc attrs that only a specific pass understands.

With this structure:
- On NVIDIA: `BufferedHandoff` can lower to TMA + `ttng.*barrier*` (similar to `nvws-lower-aref`), and
  `SubgroupPartitioning` maps to warp groups.
- On AMD: the same `BufferedHandoff` effect can lower to LDS + ROCm barrier/event primitives, or it can select a different
  schedule if the capability set cannot satisfy the protocol.
- On NPU/AIE: it can lower to DMA + events/queues, or be rejected early with a precise “missing capability” diagnostic.

This is how HTP can avoid “bail out silently because numWarps != 4” and instead:
- either choose an alternate legal strategy, or
- fail with a capability/effect mismatch that points to the missing semantic contract.

### 5.2 A solver-based pipeline is the scalable alternative to “hand-maintained pass ordering”

Triton’s autoWS pipeline is an example of ordering that is correct but non-obvious:
`PartitionScheduling → InsertAref → LowerAref → PartitionLoops → LowerWarpGroup → ScheduleLoops (+ cleanup)`.

HTP’s pipeline selection should be expressed as **constraints**:

- each stage declares `requires` and `provides` over:
  - capabilities (target features),
  - effects/protocol obligations,
  - layout facet refinement levels,
  - artifact/debug obligations.

Then a pipeline solver can:
- construct a legal pipeline for a given target + program,
- explain *why* a feature is unavailable on a target (unsatisfied constraints),
- and reduce “retargeting” from “rewrite pass pipelines by hand” to “implement capability adapters and lowerings”.

### 5.3 Backend surface area: keep it explicit and minimal

To be genuinely extensible, an HTP backend should not need to implement “whatever the current pass pipeline happens to
need”. Instead, it should implement an explicit interface such as:

- `ArchModel` (hierarchy, memory spaces, subgroup model, async primitives, barrier/event model)
- lowering hooks for:
  - `AsyncCopy`, `BufferedHandoff`, `BarrierOrEvent` effects
  - key intrinsics (e.g., tensor core families) behind capability gates
- artifact emission hooks (compile outputs + manifest + debug dumps)

This is what makes “add a new hardware target” a bounded engineering effort.

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

TileLang is a kernel DSL that explicitly targets low-level performance features, and it is implemented “on top of TVM”
(see `references/tilelang/README.md`). In that sense it is closer to Triton than to XLA:

- You get fine-grained control over kernel structure and memory usage.
- Retargetability across GPU vendors is plausible *within the GPU family* if the DSL’s semantics are carefully chosen.

However, the same core challenge appears:

- Once the DSL exposes hardware-specific concepts (warp-level behavior, shared-memory swizzles, special matrix instructions), the compiler must carry target-specific legality/performance rules.
- Supporting *non-GPU* targets (NPU/AIE) requires either a new semantic layer above these concepts or a different set of primitives.

Concrete code evidence (TileLang):

- Target capability “feature checks” are explicit and GPU-arch-shaped:
  `references/tilelang/src/target/utils.h` (e.g., `TargetIsHopper`, `TargetIsSm100`, `TargetHasAsyncCopy`, `TargetHasTmem`,
  `TargetHasBulkCopy`, `TargetIsCuTeDSL`).
- Copy lowering chooses among instruction families (Normal vs LDSM/STSM vs Bulk/TMA vs TMEM) using target features + pass
  config + legality checks:
  `references/tilelang/src/op/copy.cc` (`CopyNode::GetCopyInst` and `CopyNode::Lower`).
  It even contains backend-specific “escape hatches” (e.g., disabling raw 1D TMA for the CuTeDSL backend due to an NVPTX
  `ptxas` ICE when combined with WGMMA).

Implication: even with a shared IR substrate (TVM/TIR), high-end performance features still accumulate target-conditional
selection, legality, and lowering logic. This is good engineering, but it highlights why “retargetability” is not free: a
new target must either (a) implement an equivalent capability + legality + lowering stack, or (b) accept a reduced DSL.

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

Note: `references/` is local-only and gitignored on this branch. These paths are for reproducible code lookup if you have
the corresponding checkouts locally.

- NVIDIA backend pipeline selection (SM80/90 vs SM100+): `references/triton/third_party/nvidia/backend/compiler.py`
- Hopper warp specialization driver (SM80/90 path): `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization.cpp`
- Hopper code partition steps + comm ops insertion: `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSCodePartition.cpp`
- Upstream autoWS pipeline (SM100+ path): `references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/AutomaticWarpSpecialization.cpp`
- Partition scheduling (attrs contract): `references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/PartitionScheduling.cpp`
- Partition loops (outlining + SMEM plumbing): `references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/PartitionLoops.cpp`
- Optimize per-partition warps (pipeline re-entry): `references/triton/lib/Dialect/TritonGPU/Transforms/WarpSpecialization/OptimizePartitionWarps.cpp`
- NVWS pass semantics docs: `references/triton/third_party/nvidia/include/Dialect/NVWS/Transforms/Passes.td`
- NVWS dialect ops: `references/triton/third_party/nvidia/include/Dialect/NVWS/IR/NVWSOps.td`
- Pipelining utility attribute keys: `references/triton/include/triton/Dialect/TritonGPU/Transforms/PipeliningUtility.h`
- Loop pipelining latency assignment: `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/AssignLatencies.cpp`
- Loop pipelining scheduling: `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/ScheduleLoops.cpp`
- SWP driver pass (lower + expand + post-processing): `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/SoftwarePipeliner.cpp`
- Pipeline expander (fork of upstream pipeline transform): `references/triton/include/triton/Dialect/TritonGPU/Transforms/PipelineExpander.h`
- Pipelining utility implementation (async legality, TMA descriptor multibuffering): `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/PipeliningUtility.cpp`
- TMA store pipelining protocol: `references/triton/lib/Dialect/TritonGPU/Transforms/Pipeliner/TMAStoresPipeline.cpp`
- Top-level Python compiler driver (stages): `references/triton/python/triton/compiler/compiler.py`

## Appendix B: Code pointers (TileLang)

- Repository overview: `references/tilelang/README.md`
- Target feature checks: `references/tilelang/src/target/utils.h`
- Copy instruction selection + lowering (TMA/Bulk/LDSM/TMEM): `references/tilelang/src/op/copy.cc`
