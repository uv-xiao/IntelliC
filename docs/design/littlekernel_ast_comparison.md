# LittleKernel AST-Centric Comparison

This document closes the old programming-surface TODO about comparing HTP's
Python-AST-first compiler model with
`references/triton-distributed-knowingnothing/python/little_kernel`.

## Why this comparison matters

LittleKernel is a strong reference point because it already proves that a
Python-authored GPU DSL can feel low-level, explicit, and hardware-aware
without falling back to raw payload assembly. If HTP wants to claim a better
retargetable and agent-friendly architecture, the comparison has to be explicit.

## Visual comparison

```text
LittleKernel
Python DSL body
    -> custom Expr/Stmt IR
    -> IR passes
    -> CUDA codegen

HTP
Python-authored program
    -> canonical runnable Python AST + staged semantic payloads
    -> passes / analyses / optional islands
    -> backend package + replayable stage programs
```

## Canonical form and lowering ownership

LittleKernel keeps Python as the authoring language, but its semantic ownership
shifts quickly into its own expression / statement substrate:

- `little_kernel.language` exposes a large builtin surface
- `ll_kernel(...)` compiles the authored function into custom IR
- passes under `little_kernel/core/passes/` transform that IR before CUDA codegen

That design is coherent, but it means the canonical compiler-owned form is not
the authored Python program anymore.

HTP makes a different choice:

- the canonical form remains staged runnable Python plus attached semantic
  payloads
- semantic state such as `kernel_ir.json`, `workload_ir.json`, `types.json`,
  `layout.json`, `effects.json`, and `schedule.json` is staged beside that
  runnable Python
- optional extensions may round-trip through other IRs, but ownership returns
  to Python-space before the next global stage boundary

This difference is the core of HTP's replay story and one of the main reasons
it is more suitable for agent-oriented development.

## Schedule and dataflow authoring

LittleKernel's strongest public-surface advantage is not “it uses Python”; HTP
also does that. Its real advantage is that intermediate storage, hardware
intrinsics, and loop structure read like values in a program rather than string
slots in a payload.

Concrete examples from the reference code:

- `ll.empty(..., scope="dynamic_shared")`
- `for s in ll.unroll(range(NUM_STAGES))`
- `ll.tma_load_2d(...)`
- `ll.wgmma_compute(...)`
- explicit barrier objects and buffer arrays in one Python body

Before this comparison pass, HTP still leaked string-named scratch values in a
few public examples:

- `async_copy(A, target="a_shared", ...)`
- `mma("a_shared", "b_shared", out="accum", ...)`
- `channel_recv("tiles", out="tile_payload", ...)`

That was readable enough for proof-of-concept work, but it still looked more
like payload assembly than authored Python.

The concrete surface change landed from this comparison is:

- `async_copy(...)` now returns a typed temporary when `target=` is omitted
- `mma(...)` now returns a typed temporary when `out=` is omitted
- `channel_recv(...)` now returns a typed temporary when `out=` is omitted
- `broadcast(...)` now returns a typed temporary when `out=` is omitted
- `reduction_sum(...)` now returns a typed temporary when `out=` is omitted

That lets HTP examples read like:

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
merged = channel_recv("partials", dtype="f32", shape=("N",))
expanded = broadcast(merged, shape=("M", "N"), dtype="f32")
store(C, expanded)
```

This does not copy LittleKernel's exact DSL, and it should not. The goal is to
absorb the readability lesson while preserving HTP's shared multi-backend
compiler substrate.

## Debugging and intermediate evidence

This is where HTP has the stronger architecture.

LittleKernel has rich IR and codegen, but its main intermediate evidence is its
custom IR and generated CUDA. HTP stages a broader set of inspectable artifacts:

- runnable `ir/stages/<id>/program.py`
- semantic payloads (`kernel_ir.json`, `workload_ir.json`, `types.json`,
  `layout.json`, `effects.json`, `schedule.json`)
- analysis artifacts
- explicit rewrite maps and stage trace

That means an agent or developer can ask not only “what code did codegen
produce?” but also:

- what did the previous stage's runnable program look like?
- which semantic layer changed?
- which identities survived the rewrite?
- which backend/extension sidecar participated?

LittleKernel is a useful syntax reference. HTP is aiming at a stronger
artifact-first compiler/debug product.

## Extracted rules for HTP surfaces

This comparison yields concrete rules for future surface work:

1. Do not leak string-named scratch temporaries into flagship examples when a
   typed temporary can be returned directly.
2. Prefer expression/value flow over explicit output-slot naming in public
   code, unless the hardware contract truly needs named storage.
3. Keep backend-specific metadata as annotations on native HTP values or
   namespaced sidecars, not as a second semantic root.
4. Preserve the replayable staged-program boundary even when borrowing syntax
   ideas from lower-level DSLs.
5. When HTP adopts another surface idea from LittleKernel, tie it to the
   shared compiler model rather than introducing a backend-owned frontend.

## Remaining surface work after this comparison

This comparison is no longer just a narrative conclusion. Its extracted future
work is now tracked directly in `docs/todo/programming_surfaces.md`.

The concrete remaining frontier is:

- richer loop / region authoring that still preserves replayable Python stages
- more explicit scratch / memory-scope declarations when the temporary-returning
  path is not sufficient
- deeper workload/dataflow authoring patterns that remain as readable as the
  best LittleKernel and PyPTO examples
- continued flagship-example calibration against the reference repositories

## Coding pointers

- `htp/kernel.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `examples/csp_channel_pipeline/demo.py`
- `references/triton-distributed-knowingnothing/python/little_kernel/design/sm90_bf16_gemm.py`
- `references/triton-distributed-knowingnothing/python/little_kernel/language/`
