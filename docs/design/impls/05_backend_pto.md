# Impl: PTO / Ascend Backend Packaging (pto-runtime contract)

## Goal

Emit artifacts consumable by the Ascend PTO ecosystem for:

- simulation (`a2a3sim`)
- device execution (`a2a3`)

HTP’s PTO backend should integrate with (and largely reuse) the existing `pto-runtime` workflow: generate a kernel +
orchestration “project” and let the binding invoke `pto-runtime`’s builder to produce runnable binaries.

Local reference checkout (gitignored): `references/pto-runtime/`.

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
- optional `RUNTIME_CONFIG`: knobs like `aicpu_thread_num`, `block_dim`

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

This file is referenced from the top-level `manifest.json` via `extensions.pto.*`.

---

## 3) Manifest extensions (`manifest.json` → `extensions.pto`)

Recommended fields:

- `extensions.pto.platform`: `a2a3sim|a2a3`
- `extensions.pto.pto_runtime_contract`: `pto-runtime:<ver-or-git>`
- `extensions.pto.pto_isa_contract`: `pto-isa:<ver-or-git>` (when relevant)
- `extensions.pto.kernel_project_dir`: `codegen/pto`
- `extensions.pto.orchestration_entry`: `{source, function_name}`
- `extensions.pto.runtime_config`: resolved `aicpu_thread_num`, `block_dim`, etc.

---

## 4) Binding expectations

The PTO binding must:

1) validate that `codegen/pto/kernel_config.py` exists and is internally consistent,
2) in `mode="sim"`:
   - build using `pto-runtime` platform `a2a3sim`,
   - run via `pto-runtime`’s simulation runner,
3) in `mode="device"`:
   - build using platform `a2a3` (CANN toolchain required),
   - load generated binaries and execute via `pto-runtime` host runtime.

The binding should write build/run logs into:

- `logs/build_pto_<ts>.log`
- `logs/run_pto_<ts>.log`

and record their paths in the manifest outputs/extensions.

Deep dive: binding API contract in `docs/design/impls/07_binding_interface.md`.
