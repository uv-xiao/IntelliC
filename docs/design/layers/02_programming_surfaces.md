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
- `examples/pto/intermediate/swiglu/demo.py`
- `examples/pto/intermediate/gelu/demo.py`
- `examples/nvgpu/arknife_gemm/demo.py`

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
- `examples/workloads/serving_routine/demo.py`
- `examples/workloads/serving_routine/README.md`

### 2.3 WSP surface

The WSP surface is implemented in `htp/wsp/__init__.py`.

This is no longer just a small dict helper. It now supports two tiers:

- explicit payload construction for low-level tests
- traced `@wsp.program(...)` for public authoring

The traced form is the intended surface:

```python
@wsp.program(
    target="nvgpu-ampere",
    tile=wsp.tile(block=(32, 64, 16)),
    bind=wsp.bind(grid="block", lane="warp"),
    pipeline=wsp.pipeline(depth=2, buffering="double"),
    resources=wsp.resources(num_warps=4),
    specialize=wsp.specialize(operator="matmul"),
)
def warp_tiled_gemm(...):
    wsp.task(gemm_microtile, A_row0, B_col0, C_00, TM, TN, TK, task_id="tile_00")
    wsp.task(gemm_microtile, A_row0, B_col1, C_01, TM, TN, TK, task_id="tile_01")
    wsp.task(gemm_microtile, A_row1, B_col0, C_10, TM, TN, TK, task_id="tile_10")
    wsp.task(gemm_microtile, A_row1, B_col1, C_11, TM, TN, TK, task_id="tile_11")
```

Implemented WSP properties:

- decorator-form schedule ownership
- named WSP tasks
- explicit dependency edges through handles
- block-level task decomposition that reads like a tiled program, not like a
  pass hint list
- schedule directives as readable helper values:
  - `tile(...)`
  - `bind(...)`
  - `pipeline(...)`
  - `resources(...)`
  - `specialize(...)`
- lowering into shared workload state plus staged schedule artifacts

Semantically, the current WSP examples are calibrated against two reference
stories:

- `references/arknife/tests/python/codegen_cuda_ampere.py`
  - one CTA owns a block tile
  - warps own subtiles
  - schedule metadata explains how the CTA is launched and pipelined
- `references/triton-distributed-knowingnothing/python/little_kernel/`
  - the interesting content is the mainloop structure: tile decomposition,
    software-pipeline depth, warp allocation, and ownership of output tiles

HTP deliberately mirrors those ideas in simpler traced Python:

- `warp_tiled_gemm` models one CTA computing a `2 x 2` output-tile grid, with
  one task per warp-owned microtile
- `littlekernel_mainloop_gemm` models one CTA computing a `4 x 2` output-tile
  lattice under a deeper software-pipeline schedule

That keeps the public program semantically meaningful even though the current
surface still limits one WSP program to one kernel shape.

Important current constraint:

- the public WSP surface currently supports exactly one kernel per WSP program

That is an intentional API simplification. It constrains heterogenous task
graphs, but it still allows meaningful tiled ownership and schedule structure.

Code anchors:

- `htp/wsp/__init__.py`
- `examples/patterns/wsp/warp_tiled_gemm/demo.py`
- `examples/patterns/wsp/littlekernel_mainloop_gemm/demo.py`
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
    staged_tiles = fifo("staged_tiles", dtype="f32", capacity=2)
    routed_tiles = fifo("routed_tiles", dtype="f32", capacity=2)
    completion_tokens = fifo("completion_tokens", dtype="f32", capacity=1)
    process("stage_hbm_tile", kernel=dispatch_token_tile, args=(...), steps=[put(staged_tiles)])
    process("route_peer_tile", kernel=dispatch_token_tile, args=(...), steps=[get(staged_tiles), put(routed_tiles)])
    process("commit_remote_tile", kernel=dispatch_token_tile, args=(...), steps=[get(routed_tiles), put(completion_tokens)])
    process("retire_delivery", kernel=dispatch_token_tile, args=(...), steps=[get(completion_tokens)])
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
than the eventual framework envelope, while still allowing meaningful protocol
stories. The current flagship CSP example is calibrated against the
LittleKernel FlashComm dispatch design:

- `stage_hbm_tile` moves a token tile into a staged buffer
- `route_peer_tile` forwards the staged tile into the routed queue
- `commit_remote_tile` publishes the delivered tile and emits a completion
- `retire_delivery` drains the completion token and retires the transfer

That is a real transport protocol narrative, not a synthetic stage-label list.

Code anchors:

- `htp/csp/__init__.py`
- `examples/patterns/csp/channel_pipeline/demo.py`
- `examples/extensions/aie_channel_pipeline/demo.py`
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

There are two good extension styles today.

1. **Thin traced frontend over core kernel/routine values**
   - best when the surface is mostly syntax sugar
   - example: a future `htp_ext.collectives` surface could trace calls that
     eventually lower into ordinary workload tasks plus collective analysis

2. **Pattern frontend with its own typed spec object**
   - best when the surface needs pattern-local invariants before lowering
   - example: a future grouped-GEMM or attention frontend could build a
     dedicated public spec, validate its shape, then emit one canonical
     program payload

In both cases, the extension should make the authored Python shorter and more
readable than manual payload construction. If it adds ceremony without semantic
benefit, it is the wrong abstraction.

### Minimum extension contract

An extension surface should specify:

- how parameters are typed
- how task/process/channel/schedule structure is represented
- what canonical payload it emits
- which parts are frontend sugar versus normative payload
- how malformed usage fails
- which parts of the authored Python are normative compiler input versus
  frontend sugar
- how examples remain readable without forcing users to learn internal payload
  keys

### Review bar for new surfaces

A new surface is not acceptable just because it compiles. It must also clear
the public-language bar:

- does the example read like Python, not payload assembly?
- are important scheduling/dataflow decisions visible in the code?
- is the number of explicit helper objects justified?
- does the code feel at least as readable as the relevant `references/`
  examples?
- does the surface preserve semantic meaning, not just syntactic compactness?
  A short program that no longer communicates ownership, schedule, or protocol
  intent is still a bad public surface.

## Implemented example inventory

Programming-surface proof cases currently include:

- PTO:
  - `examples/pto/beginner/vector_add/demo.py`
  - `examples/pto/intermediate/swiglu/demo.py`
  - `examples/pto/intermediate/gelu/demo.py`
  - `examples/pto/intermediate/vector_dag/demo.py`
- NV-GPU:
  - `examples/nvgpu/arknife_gemm/demo.py`
- WSP:
  - `examples/patterns/wsp/warp_tiled_gemm/demo.py`
  - `examples/patterns/wsp/littlekernel_mainloop_gemm/demo.py`
- CSP / channel workloads:
  - `examples/patterns/csp/channel_pipeline/demo.py`
  - `examples/extensions/aie_channel_pipeline/demo.py`
- higher-level workload and extension composition:
  - `examples/workloads/serving_routine/demo.py`
  - `examples/extensions/mlir_cse/demo.py`

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
- `examples/**/README.md`

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
- WSP public surfaces currently encode tile ownership and launch structure, but
  not explicit producer/consumer warp roles inside one program body
- CSP public surfaces currently encode channel/process protocols, but not
  richer topology builders such as fan-out, join, or collective route helpers
- the public surfaces are still proof-oriented compared with the full framework
  story in `docs/story.md`

Those remaining gaps are tracked in `docs/todo/layers/02_programming_surfaces.md`.
