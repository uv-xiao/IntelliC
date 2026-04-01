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

That path is now direct as well as readable. The public surface objects expose
`to_program_module()`, and `htp.compile_program(...)` prefers that entry path
over `to_program()`. In the current implementation this is true for:
- `htp.kernel.KernelSpec`
- `htp.routine.ProgramSpec`
- `htp.wsp.WSPProgramSpec`
- `htp.csp.CSPProgramSpec`

Those frontend surfaces now share one common ingress helper in
`htp/ir/frontend.py`. Routine, WSP, and CSP no longer each hand-assemble a
`ProgramModule`; they rebuild workload/process structure and dialect metadata
through the same frontend-definition substrate.

That metadata is now richer than a flat dialect name list. Public surfaces
record a dependency-closed active dialect list plus a manifest-style activation
payload, so staged artifacts can explain not only which dialects are active but
also which frontend request produced that closure.

Compiler ingress is now slightly more formal as well. Builtin public surfaces
are registered in `htp/ir/frontends/__init__.py`, and `htp.compile_program(...)`
resolves them through frontend specs before falling back to older
`to_program_module()` / `to_program()` probing.

That frontend registry now has a rule-backed frontend-definition substrate:

- a rule-backed frontend-definition substrate now exists in
  `htp/ir/frontends/rules.py` (`FrontendRule`, `ProgramSurfaceRule`)
- builtin public surfaces are resolved through registered `FrontendSpec` objects
  in `htp/ir/frontends/__init__.py`
- builtin `htp.kernel`, `htp.routine`, `htp.wsp`, and `htp.csp` public
  surfaces now all use `rule=`-backed `FrontendSpec` registration
- `to_program_module()` on routine/WSP/CSP now delegates back through that
  registered frontend rule instead of owning a separate lowering path
- WSP and CSP public specs now carry typed top-level surface objects rather than
  raw dict payload fields:
  - `WSPTaskSpec`, `WSPDependencySpec`, `WSPScheduleSpec`
  - `ChannelRef`, `CSPProcessSpec`, `CSPProcessStep`
- remaining gap: those rules still rebuild nested stage/process-step structure
  from payload-shaped attrs rather than the final node-first rule/combinator API

Code pointers for the implemented ingress path:

- `htp/ir/frontends/rules.py`
- `htp/ir/frontends/__init__.py`
- `htp/ir/frontend.py`
- `htp/kernel.py`
- `htp/compiler.py`

The important implementation decision is that public authoring is now traced
from ordinary Python functions. A flagship example can therefore read like:

```text
@kernel
def gemm_tile(A: buffer(...), B: buffer(...), C: buffer(...), ...):
    store(C, A @ B)
```

rather than forcing public examples to assemble a nested `{"kernel": ...,
"workload": ...}` payload by hand.

That human-first rule now also applies to staged compiler artifacts. The
generated `ir/stages/<id>/program.py` files are pretty-printed runnable Python
modules with readable top-level bindings, not only a serialized payload blob.
That keeps the canonical Python-space story honest during debugging and replay,
not only at the frontend authoring boundary.

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

instead of spelling those intermediate values as string slots in every call or
dropping into raw payload fields in example code.

The repository now also supports explicit scratch declarations when implicit
temporaries stop being readable enough. Public kernels can declare storage on
native HTP values instead of inventing ad-hoc string slots:

```text
a_stages = shared_array("a_stage", count=2, dtype="f32", shape=("M", "K"))
b_stages = shared_array("b_stage", count=2, dtype="f32", shape=("K", "N"))
acc = registers("acc", dtype="f32", shape=("M", "N"))
```

Those declarations stay on the native `KernelValue` surface and preserve the
same metadata path as ordinary buffers:

- `memory_space`
- `axis_layout`
- `attrs`

This matters for retargetability. Scratch and staging are no longer special
backend-only frontends; they are now part of the shared kernel surface that can
be consumed by the normal semantic model and backend lowering.

The current surface also now supports lightweight loop/region annotation in
plain Python, and loop indices now participate in real tile/view authoring
instead of only attaching metadata to repeated ops:

```text
for stage in unroll(range(2), name="stage"):
    k0 = stage * 16
    a_view = A[:, k0 : k0 + 16]
    b_view = B[k0 : k0 + 16, :]
    with region("mainloop_stage", phase="steady"):
        async_copy(a_view, target=a_stages[stage], dtype="f32")
        async_copy(b_view, target=b_stages[stage], dtype="f32")
        barrier()
        partial = mma(a_stages[stage], b_stages[stage], m=M, n=N, k=16, dtype="f32")
```

This is still not a second loop IR. It is a traced annotation layer over
ordinary Python `for` loops, but the loop variable is now a semantic index
object and slicing syntax emits real `slice` ops on the shared HTP surface.
Emitted ops carry `attrs.regions`, `offsets`, `sizes`, and symbolic
`offset_exprs` / `size_exprs`, so replay, semantic payloads, and backend
debugging can all point at the same loop/tile evidence without leaving
Python-space.

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

The current AST-all-the-way closure proof also now has one explicit checked-in
example at `examples/tile_streamed_gemm_closure/`. It is intentionally not a
generated artifact dump. The directory contains readable committed Python
modules for:
- the surface-authored module
- the core IR module
- the scheduled/protocol-enriched module
- the backend-ready module

This gives reviewers one stable place to inspect how public authoring,
typed `ProgramModule` state, passes, and interpreter-driven execution fit
together without digging through temporary stage directories.
- task-oriented builders such as `.launch(...)`, `.mainloop(...)`, and `.after(...)`
- per-task role and stage-plan helpers such as `.role(...)`, `.prologue(...)`,
  `.steady(...)`, and `.epilogue(...)`
- schedule helpers such as `.tile(...)`, `.bind(...)`, `.pipeline(...)`,
  `.resources(...)`, and `.specialize(...)`
- workload evidence that now carries task-level `attrs.role`,
  `attrs.schedule`, and `attrs.stages` into `state.json#/items/workload_ir`

The important change is that WSP is no longer only a global schedule wrapper.
Public examples can now express a producer/mainloop/epilogue task graph in
native Python while still lowering through the same canonical HTP payload:

```text
with w.defaults(...):
    load_tiles = w.launch(task_id="load_tiles").role("producer")
    load_tiles.prologue().step("cp_async", source=w.args.A, target="a_tile")
    load_tiles.prologue().step("cp_async", source=w.args.B, target="b_tile")

    mma_tiles = w.mainloop(task_id="mma_tiles").after(load_tiles).role("consumer")
    mma_tiles.steady().step("barrier")
    mma_tiles.steady().step("mma_sync", accum="acc")
```

That structure survives into the staged workload artifacts instead of being
only a comment in the example.

Three concrete surface upgrades matter here:

- `w.defaults(...)` now scopes repeated schedule facts so flagship WSP programs
  do not repeat `.tile(...)`, `.bind(...)`, `.pipeline(...)`, and
  `.resources(...)` on every task.
- `w.args.<name>` now exposes bound kernel arguments as native `KernelValue`
  objects, so examples can stop wiring task calls through raw string tuples.
- `task.prologue()`, `task.steady()`, and `task.epilogue()` now support
  structured stage bodies via `.step(...)` objects, while the older string
  helpers remain available for compatibility tests.
- the flagship WSP examples now carry four-task narratives (`load/prefetch`,
  `mainloop/steady`, `accumulate/epilogue`, `store/writeback`) that are closer
  to the reference mainloop structure instead of a minimal two-step proof.

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
- bound kernel arguments via `p.args.<name>`
- default kernel/argument capture for `p.process(...)`
- fluent process builders such as `.process(...).role(...).compute_step(...).get(...).put(...)`
- process-local step traces that survive into `state.json#/items/workload_ir`
- public examples that now describe named dispatch/combine/writeback roles and
  protocol-local steps instead of assembling process dicts by hand
- a richer four-process flagship pipeline (`dispatch`, `combine`, `finalize`,
  `writeback`) over three explicit channels, closer to the FlashComm-style
  reference decomposition

The public surface now supports protocol narratives like:

```text
combine = p.process("combine_tiles", task_id="combine_tiles").role("router")
combine.get(tiles)
combine.compute_step("reduce_partials", channel=tiles)
combine.put(partials)

finalize = p.process("finalize_rows", task_id="finalize_rows").role("reducer")
finalize.get(partials)
finalize.compute_step("normalize_rows", channel=partials)
finalize.put(ready_rows)
```

Those authored process steps are not a second compiler substrate. They are
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

The same is now true for the schedule- and protocol-facing surfaces. WSP and
CSP no longer enter the pipeline only through raw payload dicts; they also
lower through `ProgramModule` so the shared staged-object contract applies
uniformly across the current public frontend set.

## Implemented testing baseline

The repository now applies the same human-first standard to the high-level test
suite, not only to example code. Shared authored programs live in
`tests/programs.py` and intentionally reuse public surfaces from
`examples/`:

- `examples/pto_pypto_vector_dag/demo.py`
- `examples/serving_routine/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `examples/csp_channel_pipeline/demo.py`

High-level compiler, solver, CLI, and tool tests now consume those authored
programs instead of rebuilding tiny vector-add or one-op matmul payload dicts
in each file. That matters for two reasons:

1. the tests now defend the real public programming experience rather than only
   proving that minimal payload plumbing still works
2. the readability bar from `references/pypto/`, `references/arknife/`, and
   LittleKernel is enforced continuously by regression coverage, not only by
   occasional manual example review

Raw payload dicts are still allowed in low-level backend or malformed-contract
tests when the raw artifact shape is the actual subject under test. The rule is
that public/high-level tests should default to authored Python surfaces, while
payload dicts stay reserved for contract-directed edge cases.

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

The basic programming-surface gap is closed. Further surface work, if reopened,
should be driven by a concrete new feature rather than by a standing repository
TODO. Any such work should first be reintroduced through `docs/todo/README.md`
and then implemented on top of the same native Python authoring rules described
here.

## Code pointers

- `htp/kernel.py`
- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `tests/test_public_surfaces.py`
- `tests/examples/test_examples.py`
