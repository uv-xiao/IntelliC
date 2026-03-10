# Programming Surfaces

This document describes how users currently express programs for HTP and how those surfaces converge on the shared semantic core.

## Why this topic exists

HTP is Python-AST-centric. That should mean more than “the compiler happens to store Python AST internally”. It should mean that user-facing programs are readable, inspectable Python programs and that WSP/CSP are frontend surfaces over the same compiler, not separate semantic silos.

The implemented repository proves that convergence at a limited but real scale.

## Visual model

```text
human-written Python
   |-- htp.kernel / htp.routine
   |-- htp.wsp / htp.csp
   `-- htp.ark
             |
             v
    canonical HTP program payload
             |
             v
    shared kernel/workload semantics
```

## Implemented surfaces

### Public kernel / routine surface

The repository now includes explicit public authoring helpers:

- `htp.kernel`
  - argument annotations such as `buffer(...)` and `scalar(...)`
  - traced `@kernel` authoring for single-kernel programs
  - operation helpers such as `elementwise_add(...)`, `matmul(...)`,
    `reduction_sum(...)`, `async_copy(...)`, `channel_send(...)`, and
    `channel_recv(...)`
- `htp.routine`
  - traced `@program(...)` authoring for workload-level routines
  - task helpers such as `call(...)`
  - typed channel helpers such as `fifo_channel(...)`

These helpers deliberately lower into the same canonical program payload used by
the compiler passes. They exist to keep public code readable without creating a
second semantic ownership path.

The important implementation decision is that public authoring is now traced
from ordinary Python functions. A flagship example can therefore read like:

```text
@kernel
def gemm_tile(A: buffer(...), B: buffer(...), C: buffer(...), ...):
    store(C, A @ B)
```

rather than forcing public examples to assemble a nested `{"kernel": ...,
"workload": ...}` payload by hand.

Recent frontend work also makes elementwise programs read like ordinary Python
expressions instead of builder calls. Public kernels can now use symbolic
temporaries and operator-style composition such as:

```text
gate_sigmoid = sigmoid(gate)
store(out, gate * gate_sigmoid * up)
```

This is materially closer to the readability bar set by
`references/pypto/python/pypto/language` and
`references/triton-distributed-knowingnothing/python/little_kernel/language`.

That expression-first surface now also includes literal-bearing arithmetic for
the public examples. Kernels can write:

```text
store(out, x * sigmoid(x * 1.702))
store(out, (lhs + rhs + 1.0) * (lhs + rhs + 2.0) + (lhs + rhs))
```

The current surface now applies the same rule to staged data-movement and
protocol-style operations that previously still leaked raw string scratch names.
Public kernels can write:

```text
a_shared = async_copy(A, dtype="f32", memory_space="shared")
b_shared = async_copy(B, dtype="f32", memory_space="shared")
accum = mma(a_shared, b_shared, m=M, n=N, k=K, dtype="f32")
store(C, accum)
```

and:

```text
tile_payload = channel_recv("tiles", dtype="f32", shape=("M", "N"))
tile_summary = reduction_sum(tile_payload, axis=0, dtype="f32", shape=("N",))
expanded = broadcast(tile_summary, shape=("M", "N"), dtype="f32")
store(C, expanded)
```

instead of spelling those intermediate values as string slots in every call.

without dropping into raw payload fields or explicit constant nodes in the
example code.

### `htp.compile_program(...)`

The generic compilation entrypoint already supports:
- PTO targets
- NV-GPU targets
- AIE extension targets

It captures package-level metadata, invokes solver + pipeline selection, emits staged artifacts, and hands the result to bindings and tool surfaces.

### WSP

`htp.wsp` is now a real code-backed frontend surface rather than a pure design note. It proves that workload/schedule authoring can be expressed explicitly and then lowered into the shared semantic substrate instead of creating a new compiler path.

The current proof points include:
- staged scheduling evidence
- warp-role planning
- software-pipeline planning
- shared lowering through the same pass manager and artifact model
- decorator/builder authoring through `@wsp.program(...)`
- task-oriented builders such as `.launch(...)`, `.mainloop(...)`, and `.after(...)`
- per-task role and stage-plan helpers such as `.role(...)`, `.prologue(...)`,
  `.steady(...)`, and `.epilogue(...)`
- schedule helpers such as `.tile(...)`, `.bind(...)`, `.pipeline(...)`,
  `.resources(...)`, and `.specialize(...)`
- workload evidence that now carries task-level `attrs.role`,
  `attrs.schedule`, and `attrs.stages` into `workload_ir.json`

The important change is that WSP is no longer only a global schedule wrapper.
Public examples can now express a producer/mainloop/epilogue task graph in
native Python while still lowering through the same canonical HTP payload:

```text
load_tiles = (
    w.launch(...)
    .role("producer")
    .prologue("cp_async(A->shared)", "cp_async(B->shared)")
)
mma_tiles = (
    w.mainloop(...)
    .after(load_tiles)
    .role("consumer")
    .steady("barrier", "mma_sync", "accumulate")
)
```

That structure survives into the staged workload artifacts instead of being
only a comment in the example.

### Arknife-style explicit hardware surface

`htp.ark` is now the explicit-hierarchy frontend for NV-GPU programs. It is the
implemented answer to “how does HTP absorb Arknife organically instead of
copying it as a sidecar DSL?”

The surface is intentionally close to the reference classes in
`references/arknife/python/arknife/language.py` and the CUDA reference tests:

- `@ark.build(target=..., hardware=...)`
- `ark.tensor(...)`
- `ark.axis(...)`
- `ark.spatial(...)`
- `ark.temporal(...)`
- `ark.pipeline(...)`
- `ark.attach(...)`
- instruction-level steps such as:
  - `ark.cp_async(...)`
  - `ark.ldmatrix(...)`
  - `ark.mma_sync(...)`
  - `ark.tma_load(...)`
  - `ark.wgmma(...)`
  - `ark.tma_store(...)`

The important design decision is that this does **not** introduce a second
tensor model. `htp.ark` is built on native `htp.kernel.KernelValue` objects:

- `ark.tensor(...)` is thin sugar that creates a native kernel value and
  attaches Arknife memory/layout metadata to it,
- `ark.attach(...)` lets a mixed-surface program attach the same Arknife
  metadata to an already-existing HTP value,
- instruction helpers such as `ark.cp_async(...)` and `ark.wgmma(...)` consume
  those native values directly.

`htp.ark` then lowers into the same `to_program()` payload shape as the rest of
the compiler, while adding an `ark` sidecar with:

- hardware profile metadata,
- channel declarations,
- instruction catalog metadata.

That means:

- solver selection still works through the standard target path,
- the same pass spine still stages the program,
- replay still happens through the standard stage program,
- and the NV-GPU backend still consumes the normal HTP package boundary.

In other words, Arknife’s *technique* is integrated; Arknife itself does not
become a second compiler inside the repository. This reuse boundary is the
implemented rule for future frontend extensions as well: enrich native HTP
values and routines instead of inventing parallel semantic roots.

### CSP

`htp.csp` now proves that process/channel authoring can live inside the same compiler architecture. Current CSP examples and tests show:
- typed channels
- protocol obligations
- deadlock/progress evidence
- lowering into shared workload/effect state
- decorator/builder authoring through `@csp.program(...)`
- fluent process builders such as `.process(...).role(...).compute(...).get(...).put(...)`
- process-local step traces that survive into `workload_ir.json`
- public examples that now describe named dispatch/combine/writeback roles and
  protocol-local steps instead of assembling process dicts by hand

The public surface now supports protocol narratives like:

```text
p.process("combine_tiles", ...)
 .role("router")
 .get(tiles)
 .compute("reduce_partials", channel="tiles")
 .put(partials)
```

Those `compute(...)` steps are not a second compiler substrate. They are
process-level evidence attached to the shared workload model so replay,
legality, and diagnostics can all point at the same structure.

### Workload-level routines

The repository also includes a workload-level serving routine example, which
matters because HTP is not meant to stop at kernels only. The public routine
surface now covers:

- named workload tasks
- explicit dependency edges
- typed FIFO channels
- target selection on the routine object itself
- readable auto-generated task ids when explicit names are omitted

That means public examples no longer need to express routine structure as
anonymous nested dicts just to reach the workload semantic model.

This is intentionally closer to the public feel of the `references/pypto/`,
`references/arknife/`, and LittleKernel authoring examples, while still
lowering into the shared HTP semantic substrate.

## Implemented feature inventory

Code-backed example families currently include:
- PTO vector add
- PTO fused SwiGLU
- PTO GELU
- PTO vector DAG
- NV-GPU GEMM
- NV-GPU Arknife-style Ampere GEMM mainloop
- NV-GPU Arknife-style Blackwell cluster/TMA/WGMMA GEMM
- WSP warp GEMM
- LittleKernel-calibrated WSP pipelined GEMM
- CSP channel pipeline
- AIE channel pipeline
- MLIR CSE extension composition
- serving routine workload

These examples are important because they are the public proof surface for the framework. They show which authoring claims are real today.

## Rationale for the current split

HTP deliberately separates:
- the authoring surface a user touches,
- from the semantic state the compiler stages,
- from the backend package the binding executes.

That separation is what allows one frontend surface to target multiple backends without each backend becoming the semantic owner.

## What HTP learned from LittleKernel

The completed comparison in `docs/design/littlekernel_ast_comparison.md`
pins down the actual difference between the two systems.

LittleKernel's strongest public-surface advantage is that temporary storage,
hardware intrinsics, and control constructs read like values in a program.
HTP should absorb that readability lesson, but not LittleKernel's ownership
boundary. HTP still keeps canonical ownership in runnable staged Python plus
attached semantic payloads, while LittleKernel moves into its own Expr/Stmt IR
earlier.

The latest surface pass was taken directly from that comparison: HTP now lets
data-movement and channel-style ops yield typed temporaries instead of forcing
raw string outputs in the flagship examples.

The current WSP/CSP pass extends that lesson one step further: task graphs and
protocol pipelines should read like named programs, not like schedule blobs.
That is why task roles, stage plans, process roles, and process-local compute
steps now appear explicitly in both the public examples and the staged
workload artifacts.

## Coding pointers

If you are working in this layer, start here:
- `htp/compiler.py` — generic program compilation entrypoint
- `htp/kernel.py` — public kernel authoring helpers and temporary/value flow
- `htp/routine.py` — public routine/workload authoring helpers
- `htp/wsp/__init__.py` — WSP task builders, dependencies, role/stage-plan helpers
- `htp/csp/__init__.py` — CSP process builders, role/compute-step helpers
- `htp/ark/__init__.py` — Arknife-style hardware and instruction authoring surface
- `docs/design/littlekernel_ast_comparison.md` — completed reference-backed comparison and extracted design rules
- `examples/` — runnable proof surface
- `examples/**/README.md` — example-local walkthroughs

Recent concrete proof points:
- `examples/pto_pypto_swiglu/demo.py` shows a harder PyPTO-calibrated flagship
  example authored entirely as a traced Python kernel.
- `examples/pto_pypto_gelu/demo.py` and
  `examples/pto_pypto_vector_dag/demo.py` show that literal-bearing arithmetic
  DAGs now survive replay and PTO `a2a3sim`.
- `examples/nvgpu_arknife_gemm/demo.py` uses the Arknife-style mainloop surface
  over native HTP values carrying memory-space and axis-layout metadata.
- `examples/nvgpu_arknife_blackwell/demo.py` proves that the same HTP
  programming model can author cluster/TMA/WGMMA plans for the Blackwell
  profile without creating a second compiler path.
- `examples/wsp_warp_gemm/demo.py` now shows a fluent WSP task graph with
  producer/mainloop/epilogue roles plus an op-rich staged kernel body.
- `examples/wsp_littlekernel_pipelined_gemm/demo.py` calibrates WSP schedule
  readability against LittleKernel-style pipelined GEMM code without giving up
  HTP's shared artifact model, and now stages explicit prefetch/steady/writeback
  task plans into workload evidence.
- `examples/csp_channel_pipeline/demo.py` now shows a multi-channel
  dispatch/combine/writeback protocol authored through the CSP builder surface
  with explicit process roles and named protocol-local compute steps.
- `tests/examples/test_examples.py` now defends sequential PTO example
  execution in one process so public examples remain reliable instead of being
  “one-shot” demos.

## Extension rules for programming surfaces

New public surfaces must follow the same discipline:

1. authoring stays Python-native,
2. the surface lowers into `to_program()` rather than inventing a separate
   compiler entry,
3. backend- or extension-specific metadata lives either as attached attributes
   on native HTP values or in a namespaced sidecar (`ark`, `wsp`, `csp`,
   extension package payload), and
4. the result still flows through the normal HTP pass, replay, artifact, and
   binding contracts.

That rule is now concrete because the repository has four distinct frontend
families (`kernel`, `routine`, `wsp/csp`, and `ark`) all converging on the same
compiler core.

If the work changes what “good” public authoring looks like, update both the
code examples and the example-local docs.

In practice, this means a future frontend extension should behave more like
`htp.ark.attach(...)` or the WSP/CSP role metadata than like a parallel tensor
class hierarchy. Extend native HTP values and workload records; do not fork the
semantic root.

## Current limits

The remaining surface work is no longer about basic readability. It is about
broader loop / region authoring, richer scratch-memory declarations, and
continuing to raise flagship examples toward the best reference examples. The
next gaps live in `docs/todo/compiler_model.md` and
`docs/todo/backends_and_extensions.md`, not in a separate programming-surface
comparison TODO anymore.
