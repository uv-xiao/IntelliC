# Impl: PTO / Ascend Backend Packaging (pto-runtime contract)

## Goal

Emit artifacts consumable by the Ascend PTO ecosystem for:

- simulation (`a2a3sim`)
- device execution (`a2a3`)

HTP’s PTO backend should integrate with (and largely reuse) the existing `pto-runtime` workflow: generate a kernel +
orchestration “project” and let the binding invoke `pto-runtime`’s builder to produce runnable binaries.

Local reference checkout (gitignored): `references/pto-runtime/`.

Current implementation anchors:

- emitter: `htp/backends/pto/emit.py`
- binding: `htp/bindings/pto.py`
- runtime adapter: `htp/bindings/pto_runtime_adapter.py`
- runnable example: `examples/pto_pypto_vector_add/demo.py`

---

## 1) Backend identity

- `backend`: `pto`
- `variant`: `a2a3sim | a2a3`
- `hardware_profile`: `ascend:<profile-id>` (used for legality rules and capacity/alignment constraints)

---

## 2) Artifact contract: required outputs under `codegen/pto/`

HTP should align its emitted PTO artifacts with the *current* PyPTO/Simpler-style kernel project layout (local reference:
`references/pypto/`), because that is what existing runners/tools expect.

Recommended layout:

```
codegen/pto/
  kernel_config.py               # runner-facing config/manifest (PyPTO-style)
  kernels/
    aiv/                         # AICore vector kernels (PTO ISA for a2a3; C++ loops for a2a3sim)
      <kernel_*.cpp>
    aic/                         # optional: AICore matrix kernels
      <kernel_*.cpp>
  orchestration/                 # host-side task graph builder (PTO2-style API)
    <orch_*.cpp>
  ptoas/                         # optional intermediates (PTO backend)
    <func>.pto                   # MLIR from PTO codegen
    <func>.cpp                   # C++ from ptoas
  passes_dump/                   # optional backend-local dumps (separate from HTP stage dumps)
  pto_codegen.json               # HTP-owned stable index (backend-agnostic ids)
  build/
    toolchain.json               # pinned toolchain/runtime versions + env expectations
```

### 2.1 `kernel_config.py` (runner-facing compatibility file)

Existing runners (PyPTO’s runtime runner and Simpler-style `CodeRunner`) expect a `kernel_config.py` at the project root
that declares:

- `KERNELS`: list of `{func_id, source, core_type}`
- `ORCHESTRATION`: `{source, function_name}`
- `RUNTIME_CONFIG`: runtime selection plus knobs such as `runtime`, `aicpu_thread_num`, `block_dim`, and the selected
  `platform`

HTP should emit this file as the adapter so existing build/run tooling can compile and register kernels without
HTP-specific logic.

### 2.2 `pto_codegen.json` (HTP-owned stable index)

HTP should also emit a backend-owned but HTP-shaped index that is stable across refactors:

- stable kernel ids (derived from `KernelDef` symbol path + signature + version)
- mapping:
  - `kernel_id` → `func_id`
  - `kernel_id` → source file path
  - resource requirements (UB usage estimate, vector width, async tokens, etc.)
- entrypoints:
  - workload/routine entry names → orchestration entry function name(s)

Rationale: `func_id` is a runtime/build detail; HTP needs a stable layer above it for reproducibility and agentic diffs.

### 2.3 Toolchain pinning (`build/toolchain.json`)

Capture:

- required `pto-runtime` version (contract id)
- required CANN / compiler versions (if `a2a3`)
- `PTO_ISA_ROOT` expectations (or auto-clone behavior)
- compile flags that affect ABI/semantics
- `runtime_name`
- derived build outputs under `build/pto/`:
  - `build/pto/runtime/libhost_runtime.so`
  - `build/pto/runtime/libaicpu_runtime.so`
  - `build/pto/runtime/aicore_runtime.bin`
  - `build/pto/orchestration/<entry>_orchestration.so`
  - `build/pto/kernels/<func_id>.bin`

This file is referenced from the top-level `manifest.json` via `extensions.pto.*`.

---

## 3) Manifest extensions (`manifest.json` → `extensions.pto`)

Recommended fields:

- `extensions.pto.platform`: `a2a3sim|a2a3`
- `extensions.pto.pto_runtime_contract`: `pto-runtime:<ver-or-git>`
- `extensions.pto.pto_isa_contract`: `pto-isa:<ver-or-git>` (when relevant)
- `extensions.pto.kernel_project_dir`: `codegen/pto`
- `extensions.pto.orchestration_entry`: `{source, function_name}`
- `extensions.pto.runtime_config`: resolved `runtime`, `aicpu_thread_num`, `block_dim`, etc.

---

## 4) Binding expectations

The PTO binding is the HTP-owned adapter around a real external execution implementation.

The ownership split must be explicit:

- HTP owns:
  - the emitted package contract,
  - manifest validation,
  - translation from `manifest.json` + `kernel_config.py` + `pto_codegen.json` into an execution plan,
  - normalized `validate/build/load/run/replay` result records,
  - and replay through staged Python artifacts.
- `pto-runtime` owns:
  - compilation of runtime components,
  - compilation of incore kernels and orchestration,
  - host-side loading and launch,
  - and device/simulation execution mechanics.

The local implementation references are:

- `references/pto-runtime/python/kernel_compiler.py`
- `references/pto-runtime/python/runtime_compiler.py`
- `references/pto-runtime/python/runtime_builder.py`
- `references/pto-runtime/python/bindings.py`

### 4.1 `mode="sim"` (`a2a3sim`)

For simulation, the binding should integrate with the real `pto-runtime` simulation path rather than treating PTO as a
permanent stub:

- incore kernels compile through the simulation toolchain path (`g++-15`-style host simulation build),
- orchestration compiles as a host shared library,
- runtime components build for the `a2a3sim` platform,
- `run()` uses the `pto-runtime` host bindings to initialize, launch, and finalize the runtime.

Replay still remains separate:

- `replay(stage_id)` executes HTP’s staged `program.py`,
- `run(entry)` executes the built PTO package through `pto-runtime`.

### 4.2 `mode="device"` (`a2a3`)

For hardware execution, the binding should map HTP package artifacts into the real device-oriented `pto-runtime` path:

- incore kernels compile with `ccec` and PTO ISA headers,
- orchestration compiles with the platform-appropriate host/device toolchain,
- runtime components build for `a2a3`,
- `run()` loads binaries and launches through the `pto-runtime` host API.

### 4.3 Result contract

The binding must:

1) validate that `codegen/pto/kernel_config.py` exists and is internally consistent,
2) expose structured lifecycle records for `validate/build/load/run/replay`,
3) distinguish:
   - replay failures in HTP stage artifacts,
   - build failures in toolchain/runtime integration,
   - run failures in host/device launch,
4) preserve replay even when external execution is unavailable.

The current v1 implementation uses:

- `RuntimeBuilder(platform)` to materialize host/AICPU/AICore runtime binaries,
- `KernelCompiler.compile_orchestration(...)` for orchestration `.so`,
- `KernelCompiler.compile_incore(...)` for per-kernel objects,
- `bind_host_binary(...)`, `set_device(...)`, `Runtime.initialize(...)`, `launch_runtime(...)`, and
  `Runtime.finalize()` for package execution.

The binding should write build/run logs into:

- `logs/build_pto_<ts>.log`
- `logs/run_pto_<ts>.log`

and record their paths in the manifest outputs/extensions.

Deep dive: binding API contract in `docs/design/impls/07_binding_interface.md`.

---

## 5) ArchModel (what the backend must declare, concretely)

The PTO backend must declare an `ArchModel` sufficient for legality checks and for retargetable planning passes to reason
about buffering, async transfers, and synchronization.

At minimum, PTO’s `ArchModel` should expose:

- **Hierarchy**
  - host / AICPU orchestration
  - compute cores (AIV, optional AIC)
  - logical “groups” for scheduling (block/task granularity)
- **Memory spaces**
  - global memory (GM)
  - unified buffer (UB) and any other on-chip spaces relevant to kernels
  - alignment and capacity constraints per space
- **Async primitives**
  - supported copy kinds (e.g., GM→UB, UB→GM)
  - whether copies are tokenized (awaitable) or implicitly ordered
  - concurrency limits (in-flight copies)
- **Barrier/event model**
  - what synchronization primitives exist within a kernel/task
  - what ordering guarantees are provided by the runtime

This is the boundary that lets target-neutral passes plan buffering/pipelining without embedding PTO-specific assumptions.

---

## 6) Retargetability rule: unsupported features must fail early (or be declared optional)

PTO is not a “warp execution” target in the GPU sense. Therefore:

- `Arch.Subgroup(kind=warp|wavefront)` is typically **not** provided for PTO.
- A schedule directive like `s.warp_specialize(...)` must either:
  - fail solver satisfiability early with an explicit missing capability, or
  - be declared as an *optional preference* (`s.warp_specialize(optional=True)`), in which case the solver may pick a
    pipeline that ignores it (but must record that the preference was not honored).

This is an important contract for long-term extension: “feature availability” is a capability fact, not a silent fallback.

---

## 7) Portable async/effect discharge (where PTO-specific work lives)

HTP’s portable intrinsics can express a target-neutral protocol:

- `portable.async_copy(scope="group_shared")`
- `portable.await_(token)`
- handoff protocols (producer/consumer effects)

For PTO, a backend-specific discharge pass should map these into PTO-ready operations:

- allocate UB buffers (with explicit sizes and alignment checks)
- choose DMA/copy mechanisms that PTO supports
- convert awaitable tokens into PTO’s ordering semantics (token → barrier, token → explicit wait, or “already ordered”)

Design intent:
> the PTO backend should not re-implement planning; it should discharge portable protocols into PTO primitives behind
> explicit capabilities.

This is the same structural split demonstrated in the warp specialization + pipelining case study:

- `docs/design/impls/11_case_study_warp_specialization_pipelining.md`

---

## 8) Producer-side alignment with PyPTO

HTP’s PTO package shape should continue to align with the current producer-side conventions visible in `references/pypto/`,
especially:

- orchestration vs incore function separation,
- emitted `kernel_config.py`,
- `ir.compile()`-style output structure under `kernels/` and `orchestration/`,
- and the assumption that orchestration is host-side code which dispatches incore kernels.

The point is not to copy PyPTO internals. The point is to keep the HTP-emitted package compatible with the existing PTO
tooling ecosystem.

---

## 9) What “ready to implement” means here

The PTO backend is “design-complete” when the following are explicit and testable:

- which PTO capabilities exist (ArchModel declaration + capability tags),
- which intrinsic handlers and sim/stub policies are implemented (`lower|emit`, plus simulator coverage),
- how portable async/effect protocols are discharged (which pass ids, what invariants they establish),
- the exact artifact contract under `codegen/pto/` (validated by golden artifact tests),
- and the exact adapter boundary from HTP package → `pto-runtime` compile/load/run operations.
