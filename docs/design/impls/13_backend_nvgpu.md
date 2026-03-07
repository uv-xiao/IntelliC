# Impl: NV-GPU Backend Packaging (Ampere + Blackwell)

## Goal

Provide the second mandatory v1 proof target for HTP: an NV-GPU backend that shares the same core contracts as PTO while
exercising a very different hardware model.

The design target is not “some generic CUDA backend”. It is:

- `backend = nvgpu`
- `hardware_profile = nvidia:ampere:<profile-id>` or `nvidia:blackwell:<profile-id>`

and it should use the Arknife-style explicit hardware abstraction as the reference shape for hierarchy, memory spaces,
and capability declaration.

Local design reference:

- `docs/reference/19_arknife.md`

---

## 1) Backend identity

- `backend`: `nvgpu`
- `variant`: optional toolchain/runtime variant (`cuda`, `ptx`, `triton-interop` if ever added as an extension)
- `hardware_profile`:
  - `nvidia:ampere:<profile-id>`
  - `nvidia:blackwell:<profile-id>`

The important rule is that Ampere and Blackwell are **profiles of the same backend**, not separate compiler
architectures.

---

## 2) Artifact contract: required outputs under `codegen/nvgpu/`

Recommended layout:

```
codegen/nvgpu/
  kernels/
    <kernel_*.cu>
  host/
    <launch_*.cpp or .py>
  nvgpu_codegen.json
  build/
    toolchain.json
```

Required semantics:

- `kernels/` contains `.cu` as the authoritative emitted source artifact for v1.
- derived low-level artifacts such as `.ptx` or `.cubin`, if produced, belong under `build/` as toolchain outputs rather
  than the primary codegen contract.
- `host/` contains the launch glue or binding-consumable launch metadata.
- `nvgpu_codegen.json` is the HTP-owned stable index:
  - stable `kernel_id`
  - entrypoint mapping
  - launch metadata
  - resource summaries (registers, shared memory, block shape, async/barrier features used)
- `build/toolchain.json` pins:
  - CUDA toolkit / driver contract
  - codegen mode (`cuda_source` for v1)
  - architecture targets (`sm80`, `sm90+`, blackwell-specific profile ids when finalized in implementation)

---

## 3) ArchModel contract

The NV-GPU backend must declare an `ArchModel` with, at minimum:

- **hierarchy**
  - grid
  - block / CTA
  - subgroup level(s) relevant to the profile
  - tile / instruction group where needed
- **memory spaces**
  - global memory
  - shared memory (`smem`)
  - registers
  - any profile-specific spaces/caches that become semantically relevant
- **async/barrier model**
  - async copy support and limits
  - barrier scopes
  - ordering guarantees
- **compute capabilities**
  - vector widths
  - MMA/tensor-core families
  - profile-specific features gated by capability tags

This is where Ampere vs Blackwell differences belong: in capabilities and profile parameters, not in ad-hoc pass forks.

---

## 4) Retargetability rule across Ampere and Blackwell

HTP must not encode “Ampere pipeline” and “Blackwell pipeline” as unrelated compiler worlds.

Instead:

- portable schedules and intrinsics state intent,
- the solver selects passes whose requirements match the profile,
- backend discharge passes map intent into profile-supported primitives,
- unsupported preferences fail explicitly or are recorded as unhonored optional preferences.

Examples:

- a feature available only on Blackwell must appear as a missing capability on Ampere,
- a schedule that only needs shared-memory tiling but not a newer async primitive should remain valid on both profiles.

---

## 5) Binding expectations

The NV-GPU binding must:

1) validate `codegen/nvgpu/` against the artifact contract,
2) keep `.cu` authoritative and report derived outputs separately under `build/`,
3) execute `run()` through the emitted Python host launch glue in both `sim` and `device` modes,
4) support `mode="sim"` via replay/reference semantics rather than requiring a GPU,
4) surface structured traces, logs, and stable diagnostics using the common binding API.

The common replay rule still holds:

- every stage remains runnable in `mode="sim"`,
- backend-only regions may be stubbed, but the diagnostic must be typed and recorded.

---

## 6) V1 scope

For v1, the NV-GPU backend only needs to prove the common HTP architecture on a narrow kernel set:

- vector/tile arithmetic
- explicit loads/stores
- staged schedule application
- backend lowering and artifact emission

It does **not** need to make MLIR part of the native backend path. MLIR-based flows, if used at all, are extension-owned
pipeline components.

---

## 7) Why this backend matters to the design

PTO alone is not enough to prove retargetable extensibility. NV-GPU forces HTP to survive contact with:

- a different hierarchy model,
- different memory-space semantics,
- different async/barrier assumptions,
- and profile variation across generations.

If the same core compiler substrate can serve both PTO and NV-GPU, the architecture claim becomes much stronger.
