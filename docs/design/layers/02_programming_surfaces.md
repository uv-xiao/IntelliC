# Layer 2 — Programming Surfaces

This layer describes how users currently express programs for HTP and how those surfaces converge on the shared semantic core.

## Why this layer exists

HTP is Python-AST-centric. That should mean more than “the compiler happens to store Python AST internally”. It should mean that user-facing programs are readable, inspectable Python programs and that WSP/CSP are frontend surfaces over the same compiler, not separate semantic silos.

The implemented repository proves that convergence at a limited but real scale.

## Visual model

```text
Python authoring
   |-- compile_program(...)
   |-- htp.wsp
   `-- htp.csp
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

This is intentionally closer to the public feel of the `references/pypto/` and
`references/arknife/` authoring examples, while still lowering into the shared
HTP semantic substrate.

## Implemented feature inventory

Code-backed example families currently include:
- PTO vector add
- PTO fused SwiGLU
- PTO GELU
- PTO vector DAG
- NV-GPU GEMM
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
- `examples/` — runnable proof surface
- `docs/design/examples/` — narrative walkthroughs tied to those examples

Recent concrete proof points:
- `examples/pto_pypto_swiglu/demo.py` shows a harder PyPTO-calibrated flagship
  example authored entirely as a traced Python kernel.
- `examples/pto_pypto_gelu/demo.py` and
  `examples/pto_pypto_vector_dag/demo.py` show that literal-bearing arithmetic
  DAGs now survive replay and PTO `a2a3sim`.
- `examples/nvgpu_arknife_gemm/demo.py` now uses expression-form `A @ B` plus
  `store(C, ...)` instead of explicit low-level output plumbing.
- `examples/wsp_littlekernel_pipelined_gemm/demo.py` calibrates WSP schedule
  readability against LittleKernel-style pipelined GEMM code without giving up
  HTP's shared artifact model.
- `tests/examples/test_examples.py` now defends sequential PTO example
  execution in one process so public examples remain reliable instead of being
  “one-shot” demos.

If the work changes what “good” public authoring looks like, update both the code examples and the example docs.

## Current limits

The user-facing surfaces are still narrower and more mechanical than the final intended framework. The missing work now lives in `docs/todo/layers/02_programming_surfaces.md`.
