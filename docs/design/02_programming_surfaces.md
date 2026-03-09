# Layer 2 — Programming Surfaces

This layer describes how users currently express programs for HTP and how those surfaces converge on the shared semantic core.

## Why this layer exists

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
- helper surfaces such as `task(...)`, `tile(...)`, `pipeline(...)`, and
  `resources(...)` so public WSP examples no longer need to be dominated by
  nested dict literals

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
- helper surfaces such as `fifo(...)`, `put(...)`, and `get(...)` so the public
  CSP examples read like process descriptions rather than payload assembly

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

## Coding pointers

If you are working in this layer, start here:
- `htp/compiler.py` — generic program compilation entrypoint
- `htp/kernel.py` — public kernel authoring helpers
- `htp/routine.py` — public routine/workload authoring helpers
- `htp/wsp/__init__.py` — WSP authoring helpers
- `htp/csp/__init__.py` — CSP authoring helpers
- `htp/ark/__init__.py` — Arknife-style hardware and instruction authoring surface
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
- `examples/wsp_littlekernel_pipelined_gemm/demo.py` calibrates WSP schedule
  readability against LittleKernel-style pipelined GEMM code without giving up
  HTP's shared artifact model.
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

## Current limits

The user-facing surfaces are still narrower and more mechanical than the final intended framework. The missing work now lives in `docs/todo/02_programming_surfaces.md`.
