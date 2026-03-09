# Layer 2 — Programming Surfaces

This layer defines how users write HTP programs today and how those authoring
surfaces map into the compiler’s shared Python-first semantic core.

## Why this layer matters

HTP is Python-AST-centric. That claim is meaningless if public programs still
look like nested payload assembly. The programming-surface layer therefore has a
strict job:

- let people write programs as ordinary Python functions,
- let WSP and CSP feel like language surfaces rather than manifest builders,
- and still lower into the same canonical compiler representation.

The implemented repository now proves that this can work across kernel authoring,
routine authoring, WSP scheduling, and CSP process/channel authoring.

## Design goals

The current public-surface design follows five rules.

1. **Human-first syntax**
   - public examples should read like authored Python, not JSON reconstruction
   - traced decorators and local helper calls are preferred over top-level raw
     program dicts

2. **One semantic owner**
   - public surfaces are not allowed to create parallel compiler semantics
   - all of them lower into the same canonical program payload consumed by the
     pass spine

3. **Readable specialization**
   - scheduling, pipelining, channels, and dependencies must be visible in the
     authoring code
   - they should not be hidden behind opaque string blobs or constructor soup

4. **Extension compatibility**
   - new frontends may be added without changing the compiler core’s ownership
   - extension frontends should still lower into the same canonical program
     payload shape

5. **Replay compatibility**
   - public authoring must preserve the Python-first story
   - after compilation, stages still replay as runnable Python in `sim`

## Visual model

```text
Human-written Python
    |
    |  traced decorators / helper calls
    v
Public frontend surface
    |
    |  to_program()
    v
Canonical program payload
    |
    v
semantic model + typing + passes + artifacts + replay
```

A more concrete view:

```text
@kernel              @program            @wsp.program         @csp.program
   |                    |                    |                    |
   +----------+---------+--------------------+--------------------+
              |
              v
     dict payload owned by HTP core
              |
              v
  canonicalize_program(...) + build_semantic_model(...)
```

## Implemented surfaces

### 2.1 Kernel surface

The kernel surface is implemented in `htp/kernel.py`.

It supports two modes:

- **explicit builder mode** for low-level contract tests
- **traced function mode** for public examples and high-level tests

Public authoring is expected to use the traced form:

```python
from htp.kernel import buffer, kernel, scalar, sigmoid, store

@kernel
def swiglu(
    gate: buffer(dtype="f32", shape=("size",), role="input"),
    up: buffer(dtype="f32", shape=("size",), role="input"),
    out: buffer(dtype="f32", shape=("size",), role="output"),
    size: scalar(dtype="i32", role="shape"),
) -> None:
    gate_sigmoid = sigmoid(gate)
    store(out, gate * gate_sigmoid * up)
```

Implemented public capabilities include:

- typed argument annotations with `buffer(...)` and `scalar(...)`
- symbolic expression tracing via `KernelValue`
- operator-style arithmetic such as `lhs + rhs`, `x * 1.702`, `-x`, `A @ B`
- helper ops such as:
  - `store(...)`
  - `sigmoid(...)`
  - `matmul(...)`
  - `async_copy(...)`
  - `reduction_sum(...)`
  - `channel_send(...)`
  - `channel_recv(...)`
  - `barrier()`

The key design choice is that traced kernel bodies do **not** become the
canonical IR themselves. Instead, they produce the canonical payload that the
compiler already owns. This keeps the public syntax pleasant without creating a
second compiler pipeline.

Code anchors:

- `htp/kernel.py`
- `tests/test_public_surfaces.py`
- `examples/pto_pypto_swiglu/demo.py`
- `examples/pto_pypto_gelu/demo.py`
- `examples/nvgpu_arknife_gemm/demo.py`

### 2.2 Routine / workload surface

The routine surface is implemented in `htp/routine.py`.

It is for workload-level programs that are above a single kernel invocation.
Today it provides:

- traced `@program(...)`
- `call(...)` for named kernel invocations
- `fifo_channel(...)` / `channel(...)`
- dependency specification through returned task handles and `after=...`

Example shape:

```python
@program(target="nvgpu-ampere")
def serving_routine(...):
    fifo_channel("token_batches", dtype="f32", capacity=2)
    prefill = call(decode_step, hidden, weights, next_hidden, B, H, task="prefill")
    call(decode_step, next_hidden, weights, next_hidden, B, H, task="decode", after=prefill)
```

This matters because HTP is not only a single-kernel compiler. It needs a
workload surface that can express named calls, typed channels, and explicit
dependency edges while still lowering into the same shared workload semantic
state.

Code anchors:

- `htp/routine.py`
- `examples/serving_routine/demo.py`
- `docs/design/examples/serving_routine.md`

### 2.3 WSP surface

The WSP surface is implemented in `htp/wsp/__init__.py`.

This is no longer just a small dict helper. It now supports two tiers:

- explicit payload construction for low-level tests
- traced `@wsp.program(...)` for public authoring

The traced form is the intended surface:

```python
@wsp.program(
    target="nvgpu-ampere",
    tile=wsp.tile(block=(128, 256, 64)),
    bind=wsp.bind(grid="block", lane="warp"),
    pipeline=wsp.pipeline(depth=3, buffering="double"),
    resources=wsp.resources(num_warps=8),
    specialize=wsp.specialize(operator="matmul"),
)
def pipelined_mainloop(...):
    prologue = wsp.task(gemm_tile, A, B, C_stage0, M, N, K, task_id="prologue")
    stage0 = wsp.task(gemm_tile, A, B, C_stage1, M, N, K, after=prologue, task_id="stage0")
    stage1 = wsp.task(gemm_tile, A, B, C_stage0, M, N, K, after=stage0, task_id="stage1")
    wsp.task(gemm_tile, A, B, C, M, N, K, after=stage1, task_id="epilogue")
```

Implemented WSP properties:

- decorator-form schedule ownership
- named WSP tasks
- explicit dependency edges through handles
- schedule directives as readable helper values:
  - `tile(...)`
  - `bind(...)`
  - `pipeline(...)`
  - `resources(...)`
  - `specialize(...)`
- lowering into shared workload state plus staged schedule artifacts

Important current constraint:

- the public WSP surface currently supports exactly one kernel per WSP program

That is an intentional simplification of the public API, not a statement about
the long-term framework. The current implementation prefers a readable,
testable surface over prematurely generalizing task graphs with heterogeneous
kernels.

Code anchors:

- `htp/wsp/__init__.py`
- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `tests/test_public_surfaces.py`
- `tests/examples/test_examples.py`

### 2.4 CSP surface

The CSP surface is implemented in `htp/csp/__init__.py`.

Like WSP, it now has both:

- explicit payload construction for low-level contract tests
- traced `@csp.program(...)` for public authoring

The traced form is now the preferred way to express process/channel structure:

```python
@csp.program(target="nvgpu-ampere")
def channel_pipeline(...):
    tiles = fifo("tiles", dtype="f32", capacity=2)
    partials = fifo("partials", dtype="f32", capacity=1)
    completions = fifo("completions", dtype="f32", capacity=1)
    process("prefetch", kernel=gemm_tile, args=(...), steps=[put(tiles), put(partials)])
    process("compute", kernel=gemm_tile, args=(...), steps=[get(tiles), get(partials), put(completions)])
    process("epilogue", kernel=gemm_tile, args=(...), steps=[get(completions)])
```

Implemented CSP properties:

- typed channels via `channel(...)` / `fifo(...)`
- readable step events via `put(...)` and `get(...)`
- traced process registration via `process(...)`
- automatic channel registration inside traced program bodies
- auto task-id generation when `task_id` is omitted
- lowering into shared workload + effect state
- protocol analysis and deadlock/progress checks in later passes

Important current constraint:

- the traced CSP surface currently supports exactly one kernel per CSP program

That mirrors the current WSP simplification and keeps the public API smaller
than the eventual framework envelope.

Code anchors:

- `htp/csp/__init__.py`
- `examples/csp_channel_pipeline/demo.py`
- `examples/aie_channel_pipeline/demo.py`
- `tests/test_public_surfaces.py`
- `tests/examples/test_examples.py`

## Why traced surfaces are the right implementation choice

There were three plausible public-surface directions:

1. raw dict payloads
2. constructor-heavy spec objects
3. traced Python functions that still lower into the canonical payload

HTP intentionally chose option 3.

### Why not raw dicts

Raw dicts are acceptable for low-level contract tests, but they are the wrong
flagship surface because they:

- expose internal payload details too early
- make examples look like manifest authoring, not program authoring
- encourage frontend drift because every example becomes a custom payload

### Why not constructor soup

A purely object-builder surface can be type-safe, but it still fails the
human-first goal when simple programs become stacks of nested constructor calls.
That is exactly the kind of authoring style this repository now rejects for
flagship examples.

### Why traced Python works here

Traced functions fit HTP’s architecture because they give:

- native Python syntax
- a clear place to attach typing via annotations
- readable local names and control flow
- a deterministic lowering point into the canonical program payload

Most importantly, the traced public surface is **not** the compiler’s semantic
owner. It is a frontend that lowers into the compiler-owned payload and then
into the shared semantic model.

## How these surfaces lower

The lowering contract is:

```text
decorated/traced public object
    -> .to_program()
    -> canonicalize_program(...)
    -> build_semantic_model(...)
    -> build_type_layout_effects(...)
    -> schedule / passes / artifacts / replay
```

Concretely:

- `KernelSpec.to_payload()` lowers public kernel authoring into the canonical
  kernel payload
- `ProgramSpec.to_program()` lowers routine/workload authoring
- `WSPProgramSpec.to_program()` lowers WSP tasks + dependencies + schedule
- `CSPProgramSpec.to_program()` lowers channels + processes

That means the frontends are allowed to be ergonomic, but they are **not**
allowed to invent new downstream contract shapes ad hoc.

## Extension model for new programming surfaces

This layer also defines how new authoring surfaces should be added.

### Rule: extend by lowering, not by bypassing

A new public surface should:

1. expose a user-facing Python API
2. trace or build that surface into a typed public spec object
3. implement `to_program()`
4. emit the same canonical payload family the core compiler already accepts

Do **not** add a new frontend by:

- calling private pass helpers directly
- emitting semantically incomplete dicts that rely on later passes to guess
  intent
- bypassing `compile_program(...)`
- or making a backend the semantic owner of the public syntax

### Recommended extension shape

```text
htp_ext/<surface>/
    __init__.py        public syntax
    spec.py            dataclasses / typed public objects
    lowering.py        to_program() helpers
    tests/             focused public-surface tests
```

### Minimum extension contract

An extension surface should specify:

- how parameters are typed
- how task/process/channel/schedule structure is represented
- what canonical payload it emits
- which parts are frontend sugar versus normative payload
- how malformed usage fails

### Review bar for new surfaces

A new surface is not acceptable just because it compiles. It must also clear
the public-language bar:

- does the example read like Python, not payload assembly?
- are important scheduling/dataflow decisions visible in the code?
- is the number of explicit helper objects justified?
- does the code feel at least as readable as the relevant `references/`
  examples?

## Implemented example inventory

Programming-surface proof cases currently include:

- PTO:
  - `examples/pto_pypto_vector_add/demo.py`
  - `examples/pto_pypto_swiglu/demo.py`
  - `examples/pto_pypto_gelu/demo.py`
  - `examples/pto_pypto_vector_dag/demo.py`
- NV-GPU:
  - `examples/nvgpu_arknife_gemm/demo.py`
- WSP:
  - `examples/wsp_warp_gemm/demo.py`
  - `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- CSP / channel workloads:
  - `examples/csp_channel_pipeline/demo.py`
  - `examples/aie_channel_pipeline/demo.py`
- higher-level workload and extension composition:
  - `examples/serving_routine/demo.py`
  - `examples/mlir_cse_extension/demo.py`

These examples matter because they are the public proof that the programming
surface is real, not merely documented.

## Coding pointers

If you are changing this layer, start here:

- `htp/kernel.py`
- `htp/routine.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `htp/compiler.py`
- `tests/test_public_surfaces.py`
- `tests/examples/test_examples.py`
- `examples/`
- `docs/design/examples/`

Reference calibration anchors:

- `references/pypto/examples/language/`
- `references/pypto/python/pypto/language/`
- `references/arknife/tests/python/`
- `references/triton-distributed-knowingnothing/python/little_kernel/`

## Current implemented limits

The repository is materially better than the old payload-shaped public surface,
but the final framework envelope is broader than what is implemented today.

Current limits that still remain outside `docs/design/`:

- the full written HTP-vs-LittleKernel AST-centric comparison is still tracked
  in `docs/todo/reports/littlekernel_ast_comparison.md`
- WSP and CSP still intentionally constrain traced public programs to one kernel
  each
- the public surfaces are still proof-oriented compared with the full framework
  story in `docs/story.md`

Those remaining gaps are tracked in `docs/todo/layers/02_programming_surfaces.md`.
