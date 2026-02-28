---
# Findings & Decisions

## Requirements
- Produce a comprehensive research report on retargetable extensibility in ML compilers.
- Compare HTP goals vs Triton, JAX, TileLang; focus on heterogeneous hardware.
- Analyze MLIR-style IR+pass construction limits and propose better mechanisms.
- Use Triton roadmap (warp specialization) + Triton codebase exploration with concrete pass/file references.
- Consider the opinion in `references/size-littlekernel.md`.

## Research Findings

### Initial repo state (HTP docs-only branch)
- Active HTP redo docs live in `docs/future-htp/`.
- PTO-WSP v9/v10 designs are preserved as reference in `docs/reference/pto-wsp/`.
- `references/` is gitignored and used for large local checkouts.

### Zhihu / LittleKernel notes (from `references/size-littlekernel.md`)
- Argues for Python-AST-as-DSL enabling concise kernels and rapid compiler construction.
- Emphasizes the gap between heavy compiler infrastructures (team-years) vs relatively direct underlying ideas.
- Motivates an approach where compiler logic is expressed as Python-level transformations and codegen, aided by strong tooling/LLMs.
- Provides a Hopper GEMM example in a “LittleKernel” DSL showing complex scheduling primitives (TMA, mbarriers, warpgroup regs, swizzles) expressed in a compact Python surface.

(Need: extract the post’s specific criticisms of MLIR/pass-based designs and any proposed alternative constraints.)

## Decisions
| Decision | Rationale |
|----------|-----------|
| Plan to clone Triton into `references/triton/` | Required for code-grounded analysis |
| Use warp specialization + async memory pipeline as case studies | Matches Triton roadmap + heterogeneous constraints |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Tool commands failed due to missing original repo path | Use explicit workdir `/home/uvxiao/htp` |

## Resources
- Triton roadmap blog (warp specialization): https://pytorch.org/blog/warp-specialization-in-triton-design-and-roadmap
- Triton repo: https://github.com/triton-lang/triton
- LittleKernel opinion: `references/size-littlekernel.md`

## Visual/Browser Findings
- (none yet)

### Triton roadmap (2026-01-08) — autoWS design + roadmap highlights
From the PyTorch blog “Warp Specialization in Triton: Design and Roadmap”:

- autoWS is developed primarily in Meta’s OSS mirror `facebookexperimental/triton` and only partly upstreamed.
- autoWS is described as a sequence of compiler passes (in order):
  1) data partitioning (create more independent GEMMs/ops to schedule)
  2) Loop Scheduler: create SWP schedule (heuristics) and attach decisions as attributes
  3) Partition Scheduler: partition code into warp partitions, decisions as attributes
  4) Buffer Creation: build inter-partition comm buffers in SMEM or TMEM
  5) Memory Planner: decide buffer copies/reuse, annotate allocs with IDs/offsets/copies
  6) Code Partitioner: create producer-consumer channels + lower to buffers + barriers; outline partitions
- A key engineering pattern: many decisions are “passed via op attributes” between passes.
- Short-term directions include: profile-guided partition scheduling, profile-guided SWP scheduling (modulo scheduling), memory planner improvements (autotune), ping-pong scheduling, region-based explicit subtiling, debug tooling, IR improvements (using `aref` and delaying lowering).
- Future directions explicitly call out global cost-model-driven optimization and language support that separates computation from data/schedules (Halide-like ideas).

Implication for this research: Triton’s path to SOTA requires an expanding set of backend- and architecture-specific scheduling/memory/sync features, and relies on non-trivial pass interactions with implicit invariants carried in attributes.

### Older PyTorch warp specialization post (TTGIR comm ops)
A separate PyTorch blog post “Warp Specialization” notes (summary snippet):
- Introduces high-level TTGIR communication operations (ProducerAcquire/Commit/ConsumerWait/Release) to manage pipelined dataflows.
- Code partitioning outlines each async task into its own code region guarded by warp group ID checks.
- Communication ops eventually materialize into LLVM/PTX barrier operations.

Implication: even within Triton’s stack, supporting advanced pipelining/synchronization required *new IR ops* and a dedicated lowering strategy, with significant backend materialization work.

### Triton code (official `triton-lang/triton`) — concrete warp specialization pipeline
From `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization.cpp` and `WSCodePartition.cpp`:

- Warp specialization is implemented as an NV Hopper-specific transform library (`NVHopperTransforms`) that wires together multiple internal steps:
  - `doTaskPartition(funcOp, numWarpGroups)`
  - `doTaskIdPropagate(funcOp)` (can fail with `-1`)
  - `doDataPartition(funcOp, numWarpGroups - 1)`
  - `doCodePartition(funcOp, numStages)`
  - `doTokenLowering(funcOp, numWarpGroups - 1)`
  - `invalidateWarpSpecializeBarriers(funcOp)`
- The pass is gated by multiple *hard assumptions*:
  - It only triggers on loops with `kWarpSpecializeAttrName` and `num_stages > 1`.
  - It bails out unless `lookupNumWarps(funcOp) == 4`.
  - It currently bails out if there is any `scf.if` with an else block (explicit TODO about handling channels in else blocks).
  - It iterates `numWarpGroups` from 3 down to 2 as a heuristic search.
- `WSCodePartition.cpp` shows a multi-step code partitioning pipeline with explicit phases, including:
  - Step 5: create channel buffers
  - Step 6: insert async copies (and local copies)
  - Step 7: create tokens/barriers for channels
  - Step 8: insert async comm ops (ProducerAcquire/Commit/ConsumerWait/Release) and lower TMA loads

Concrete file locations:
- `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization.cpp`
- `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSCodePartition.cpp`
- NVWS ops: `references/triton/third_party/nvidia/include/Dialect/NVWS/IR/NVWSOps.td`

Implication: even within an MLIR-style pass framework, high-end features require deep backend-specific transforms, new dialect ops, and a pile of implicit invariants (numWarps, control-flow restrictions, interaction with num_stages/SWP).

### Triton code — warp specialization is cross-cutting (not one pass)
Additional code-level evidence from `references/triton/include/triton/Dialect/TritonGPU/Transforms/PipeliningUtility.h` and `AssignLatencies.cpp`:

- Core transform utilities define shared attribute keys used across multiple transforms:
  - `tt.num_stages` (`kNumStagesAttrName`) for SWP/pipelining
  - `tt.warp_specialize` (`kWarpSpecializeAttrName`) for warp specialization
  - additional scheduling attributes like `loop.stage`, `loop.cluster`, `tt.scheduled_max_stage`
- Loop pipelining (`AssignLatencies.cpp`) contains explicit special-casing for warp specialization:
  - comments about SWP vs WS interactions and hacky heuristics (e.g., `scf.if` behavior, accumulator multibuffering)
  - conditional behavior depending on whether a loop (or parent loops) carries `tt.warp_specialize`

Also, `rg` shows warp specialization touches:
- analyses (`lib/Analysis/*`),
- conversion to LLVM (`lib/Conversion/TritonGPUToLLVM/*`),
- utility headers (`include/triton/Conversion/TritonGPUToLLVM/WarpSpecializeUtility.h`),
not just the NV Hopper-specific transform library.

Implication: adding a “single optimization feature” (warp specialization) rapidly becomes a *whole-stack feature* spanning IR attrs, analyses, scheduling heuristics, lowering, and backend-specific dialect ops.

### Triton compilation driver — stage pipeline + backend-registered stages
From `references/triton/python/triton/compiler/compiler.py`:

- Triton’s compiler is structured as a *stage pipeline* keyed by file extensions (`ttir`, `ttgir`, `llir`, `ptx/amdgcn`, `cubin/hsaco`, etc.).
- Backends register stage functions via `backend.add_stages(stages, options, src.language)`.
- `make_backend(target)` selects exactly one backend whose `supports_target(target)` matches.
- The driver caches each stage output and supports overriding/dumping IR per stage.

Implication: backend retargeting is not “just add a lowering”: it requires defining the stage graph, dialect loading, codegen implementations, and binary packing/loading hooks.

### Triton repo structure shows backend split
`references/triton/third_party/` includes `nvidia/` and `amd/` trees, with major transforms (e.g., Hopper warp specialization) living under NVIDIA-specific `third_party/nvidia/...`.

### Triton lowering abstraction is still GPU-shaped (TargetInfoBase)
From `references/triton/include/triton/Conversion/TritonGPUToLLVM/TargetInfoBase.h`:

- Triton defines a backend interface for lowering that includes GPU-specific primitives:
  - warp shuffles (`shuffleXor/Up/Idx`), ballot, warpSync, warpReduce
  - programId semantics
  - shared memory address space and (optional) cross-CTA shared transfers
- This is a useful abstraction for *CUDA vs ROCm*, but it encodes a GPU execution model.

Implication: retargeting to non-GPU accelerators (e.g., AIE spatial arrays, NPU tiles with different sync/memory) likely requires redesigning the “portable lowering interface”, not just implementing a new backend.

### LittleKernel (size-littlekernel.md) — key opinions relevant to HTP/MLIR
Key claims in `references/size-littlekernel.md` (translated/paraphrased):

- *No new IR*: “Python AST is the IR.”
- *Minimize passes*: only do required passes; focus on the emitter.
  - Suggested “must-have” passes: const-folding, inlining, type inference.
  - Other passes are mostly syntactic sugar; use short Python AST mutators.
- *Hot-pluggable intrinsics*: treat hardware-specific instructions as attributes/intrinsics that can be registered ad-hoc with codegen rules.
- *Retargeting worldview*: hardware is fragmenting; there is no single unified programming model beyond control flow + structs.
  - Therefore “switching hardware should only require switching the emitter”, and defining new intrinsics as needed.
- *Productivity constraint*: “don’t leave Python”; keep compilation lightweight and keep C++-level control.
- Notes vendors may not expose low-level IR; emitter-to-source approach can integrate quickly.

Tension to analyze in the report:
- This approach prioritizes *fast, manual, hardware-specific kernel authoring*.
- It downplays (but doesn’t eliminate) the need for typed semantic contracts across passes/backends when composing larger systems (pipelines/serving routines/multi-backend correctness).

### Triton example: “async copy” is not portable semantics; it is backend instruction constraints
From `references/triton/third_party/nvidia/lib/TritonNVIDIAGPUToLLVM/LoadStoreOpToLLVM.cpp` (cp.async lowering):

- cp.async has hard constraints enforced in lowering:
  - transfers smaller than 4 bytes are rejected (`cp.async does not support transfers smaller than 4 bytes`).
  - cross-CTA loads are rejected (`cp.async does not support cross-cta loads`).
  - non-trivial “block” dimension layouts are rejected (`cp.async does not support non-trivial block dimension`).
- The lowering chooses cache modifiers (CG vs CA) based on transfer size.

Implication: the *meaning* of “async copy” depends on detailed instruction legality constraints (layout/contiguity/mask alignment). Retargeting this to other hardware requires either:
- defining a portable async-copy semantic layer with capability/legality checks per backend, or
- baking per-backend rules throughout the pipeline.

### Triton warp specialization task partitioning depends on NVIDIA-specific ops
From `references/triton/third_party/nvidia/hopper/lib/Transforms/WarpSpecialization/WSTaskPartition.cpp`:

- `doTaskPartition` searches the function for:
  - `ttng::WarpGroupDotOp` (NVIDIA-specific warp-group MMA op)
  - `tt::LoadOp` / `tt::DescriptorLoadOp`
  - `tt::StoreOp` / `tt::DescriptorStoreOp`
- It selects producer ops by taking a backward slice from the dot operands and picking expensive loads / descriptor loads.
- It annotates ops with async task IDs (`setAsyncTaskIds`) which later passes use to outline partitions and build channels.
- It bails out if user annotations already exist (non-empty async task IDs).

Implication: “warp specialization” is not expressed in a backend-neutral way; its key partitioning signal is a backend-specific op (`WarpGroupDotOp`). Retargeting would require defining an equivalent op or lifting the partitioning criteria into a backend-neutral contract.

### Triton backend reality: per-vendor, per-arch pass pipelines hard-code feature logic
From `references/triton/third_party/nvidia/backend/compiler.py` (`make_ttgir`) and `references/triton/third_party/amd/backend/compiler.py` (`make_ttgir`):

- NVIDIA backend `make_ttgir` has explicit compute-capability branching that changes the pass pipeline:
  - for SM80/SM90: runs Hopper warp specialization via `nvidia.passes.hopper.add_hopper_warpspec(...)` then `assign_latencies`, `schedule_loops`, `pipeline`.
  - for SM100+: adds additional passes: `optimize_accumulator_init`, `hoist_tmem_alloc`, `promote_lhs_to_tmem`, `add_warp_specialize`, `optimize_partition_warps`, `remove_tmem_tokens`, etc.
  - also includes `tma_lowering` for SM90+.
- AMD backend `make_ttgir` is a different pipeline (AMD-specific passes and knobs):
  - scheduling/pipelining decisions depend on `gfx*` arch and flags like `use_async_copy`, `use_block_pingpong`, etc.

Implication: performance-critical features are encoded as backend-specific pass pipelines with arch-dependent conditions. Retargeting to “many hardware targets” means either:
- a proliferation of similar-but-different pipelines, or
- creating a more explicit, typed contract layer that lets multiple backends share transformations without duplicating logic.
