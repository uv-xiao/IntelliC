# HTP Substrate Completion Design

**Date:** 2026-03-08

## Goal

Define the next large completion phase for HTP so the framework becomes a real compiler rather than a replay/package shell.
The target is:

1. complete the **core substrate**,
2. complete the **extension substrate**,
3. then drive **real working backends** from that substrate.

The agreed ordering for execution is:

1. **C — complete the semantic and typing substrate**
2. **A — make NV-GPU consume it for a real numerical path**
3. **B — make PTO `a2a3sim` consume it for a real numerical path**

This is not a “minimal viable compiler” plan. The intent is to implement enough substrate that HTP’s architectural claim is
visible in code.

## Scope boundary

The selected boundary is **core + extension substrate complete**.

That means this phase must make the following real:

- the kernel/workload semantic model,
- type/layout/effect/schedule state,
- pass contracts over that state,
- staged artifact emission of that state,
- extension-owned passes and island evidence,
- backend lowerers that consume the staged semantic model.

What is explicitly **not** required in this phase:

- implementing every future backend,
- making MLIR the native owner of semantics,
- pulling all roadmap material from `docs/future/design/` into code.

## Semantic core

The semantic core remains Python-first. Python AST is still the canonical compiler form, and every stage remains runnable in
`sim`. The change is that stages must now carry a real typed semantic payload rather than the current tiny demo metadata.

The semantic substrate should have two top-level models:

- **Kernel IR**
  - values: scalar, tensor, buffer handle, view, async token
  - storage: buffers, aliases/views, memory-space placement
  - control: loop, if, block, region
  - ops: load/store, unary/binary elementwise, reduction, cast, broadcast, transpose/view, abstract `mma`, async copy,
    await, barrier

- **Workload IR**
  - entry signatures and argument schemas
  - task/process nodes
  - channels / queues / dependencies
  - workload-to-kernel calls
  - explicit side effects for send/recv/synchronization

These models are not separate semantic owners. They are typed staged attachments emitted beside `program.py` and consumed by
passes and backends.

## Typing substrate

The compiler must carry four explicit state layers per stage:

- **type state**: value kinds, dtypes, ranks, shapes, aliases
- **layout state**: logical layout, tiling, distribution intent, memory-space placement
- **effect state**: reads/writes, tokens, barriers, channel protocol effects
- **schedule state**: mapping, tiling, specialization, pipelining, launch structure

These states must be operational, not documentary. Passes and validators consume them. Backends lower from them. Diagnostics
must point to them.

The mandatory operation surface for the first real semantic core is:

- kernel semantics,
- workload/dataflow semantics,
- first-class channels/processes,
- broad operation coverage rather than a tiny elementwise subset.

This is the minimum needed to show why HTP is different from “just another kernel code emitter”.

## Pass substrate

Passes must stop operating on `{"entry": ..., "ops": [...]}`-style placeholders. They must consume and update explicit
semantic state.

The intended pass spine is:

1. capture / canonicalize
2. semantic model construction
3. type/layout/effect checking
4. schedule analysis
5. schedule application
6. backend lowering
7. package emission

Every pass must declare:

- the state layers it requires,
- the analyses it requires,
- the state layers it updates,
- whether it mutates AST, semantic state, or both.

Each stage must emit:

- `program.py`
- semantic payloads (`kernel_ir.json`, `workload_ir.json`, `types.json`, `layout.json`, `effects.json`, `schedule.json`)
- `analysis/index.json`
- `ids/*.json`
- optional `maps/*.json`

This is the mechanism that keeps the system replayable while making the compiler meaningfully typed.

## Extension substrate

The extension substrate must become real enough that optional mechanisms do not bypass the core contracts.

Three extension seams are required:

- **extension passes**
  - registered like core passes
  - consume/produce the same semantic layers
  - may emit namespaced analyses

- **extension islands**
  - may round-trip a region through another IR or toolchain
  - must return updated semantic state and updated runnable Python stage
  - must write evidence under `ir/stages/<id>/islands/<name>/...`

- **extension runtime hooks**
  - use the existing runtime extension hook
  - remain externally owned and do not take over core semantics

This is enough to make the extension substrate real without forcing all of `docs/future/design/` into the core package.

## Backend consequences

Once the substrate is real, backend work becomes constrained and testable.

### NV-GPU

The NV-GPU backend must lower from real kernel IR + schedule/layout state. The current dummy zero-argument kernel path must
be replaced with:

- real arguments,
- real indexing,
- real loads/stores,
- real numerical work,
- real launch metadata tied to the lowered kernel.

This is the first backend target because the current artifact package is visibly hollow and the machine provides A100 GPUs.

### PTO

The PTO backend must lower from real kernel/workload IR and then materialize:

- real kernel argument layout,
- real orchestration argument layout,
- real task creation and dependencies,
- real `a2a3sim` numerical behavior through `pto-runtime`.

The current smoke-run path was necessary to establish ABI correctness, but it is not sufficient as the final framework state.

## Error handling and robustness rules

This phase must aggressively remove ad-hoc behavior.

Required rules:

- no silent fallback across contract boundaries,
- no backend-specific logic leaking into generic runtime or pass layers,
- no hidden dependence on absolute paths,
- environment variables only when the toolchain genuinely requires them and after explicit contract resolution,
- conditional branches must reflect architecture or contract differences, not local convenience hacks.

All failures must be structured:

- validation failures point to malformed artifacts,
- replay failures point to staged Python artifacts and diagnostics,
- backend failures point to build/load/run logs and exact contract inputs.

## Milestones

### Milestone 1 — semantic substrate

- real kernel/workload semantic model
- staged semantic artifacts
- lowerers stop using demo-only metadata

### Milestone 2 — typing substrate

- explicit type/layout/effect/schedule state
- real legality checks and diagnostics

### Milestone 3 — extension substrate

- extension passes and extension island evidence become real

### Milestone 4 — NV-GPU numerical path

- real numerical kernel on device and replay/sim

### Milestone 5 — PTO numerical `a2a3sim` path

- real orchestration + kernel argument marshaling and numerical validation

## Acceptance criteria

The phase is complete only when all of the following are true:

- backends consume a real staged semantic model instead of placeholder metadata,
- stages emit semantic artifacts that match the implemented compiler state,
- type/layout/effect/schedule validation produces structured diagnostics,
- at least one extension-owned path updates semantic state without bypassing replay or artifact contracts,
- the NV-GPU example performs real numerical work on device,
- the PTO example performs real numerical work in `a2a3sim`,
- the design/docs split remains honest: `docs/design/` documents implemented behavior, `docs/future/design/` holds the
  roadmap and research surface,
- `pytest` and `pre-commit run --all-files` pass.

## Execution note

This work should be implemented milestone by milestone, not as an undifferentiated refactor. The principal risk is not
technical impossibility; it is contract drift caused by trying to deepen core semantics and backend behavior at the same
time without freezing each substrate layer first.
