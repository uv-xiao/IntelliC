# Backends and Extensions

This document describes how implemented targets and extension packages consume the shared compiler substrate.

## Why this topic exists

HTP is trying to support multiple hardware targets without letting each backend become a separate compiler architecture. The implemented repository already proves that this is practical at a meaningful scale:
- PTO runs through a real runtime adapter path.
- NV-GPU runs through a real CUDA path from emitted `.cu` sources.
- AIE exists as an extension-owned toolchain path.
- CPU reference packages exist as a lightweight host backend over the same semantic substrate.
- MLIR CSE exists as an extension-owned round-trip path.

The rule across all of them is consistent: core HTP owns semantics and artifacts; backends and extensions consume those contracts.

## Visual model

```text
shared semantics and staged artifacts
        |          |           |             |
        v          v           v             v
       PTO       NVGPU      AIE(ext)     CPU_REF(ext)
                     \
                      \-> MLIR CSE(ext round-trip)
```

## Implemented backend inventory

### PTO

Implemented today:
- PTO lowerer and emitter.
- Binding lifecycle support.
- Real `pto-runtime` integration.
- Numerical `a2a3sim` example path.
- Explicit `a2a3` package/runtime contract and adapter provenance.

The current PTO path demonstrates both simulation and device-shaped package contracts, with build records carrying compiler and ISA provenance.

### NV-GPU

Implemented today:
- `.cu`-first artifact ownership.
- NV-GPU lowerer and emitter.
- CUDA adapter with real build/launch path.
- GEMM example with real CUDA execution.
- Explicit Arknife-style hardware/profile metadata in codegen artifacts.
- Explicit Arknife-style instruction-plan metadata for Ampere and Blackwell.
- Profile-specialized plan metadata, NVCC flag contracts, and emitted perf records.

The current NV-GPU path now also consumes compiler-owned tile/view semantics directly:
- native Python slicing on kernel values lowers into explicit `slice` ops in `state.json#/items/kernel_ir`;
- the NV-GPU solver declaration advertises `slice` as a supported shared-semantic op instead of treating it as an Arknife-only side channel;
- flagship WSP examples compile through that same shared substrate, then validate and replay through the normal NV-GPU binding path.

This is the current proof that HTP can own the source artifact while delegating execution policy to the binding/adapter layer.

#### Arknife integration inside NV-GPU

The important new point is that Arknife-style targeting is now implemented as a native HTP path, not a disconnected example convention.

What is real today:
- Ampere and Blackwell remain profiles of the same `nvgpu` backend.
- `htp.ark` programs lower into the standard HTP program model.
- `htp.ark` no longer owns a separate tensor class; it attaches Arknife memory-space and axis-layout metadata to native `htp.kernel.KernelValue` objects.
- the NV-GPU lowerer inspects the `ark` sidecar and validates profile/capability compatibility.
- the emitted `nvgpu_codegen.json` now carries:
  - the hardware profile summary,
  - the channel plan,
  - the per-kernel instruction plan,
  - and the profile-specialized execution plan.
- the emitted `.cu` source keeps those instruction decisions visible as annotated comments while preserving a numerically-correct fallback kernel body.
- the runtime adapter records `metrics/perf.json` and returns structured timing payloads for device execution.

That is an important architectural step. It means explicit hardware and instruction planning now exist as first-class compiler facts inside HTP’s backend contracts instead of living only in reference notes.

### AIE extension backend

Implemented today:
- AIE planning analyses referenced from `stage.json`.
- AIE MLIR artifact emission.
- Reference toolchain build outputs.
- Host-runtime launch path through the binding-owned adapter.
- Launch-plan build sidecars and runtime perf records.

This proves that extension-owned backends can still participate in the same artifact and workflow discipline.

## Implemented extension inventory

### MLIR CSE

The MLIR CSE extension proves that HTP can run an extension-owned round-trip path while preserving stage discipline, artifact evidence, and identity/mapping behavior.

What is implemented today:
- extension-owned export/import passes participate in the normal solver and pass-trace flow;
- the extension can round-trip the broader scalar integer elementwise subset (`add`, `sub`, `mul`, `div`);
- replay uses the imported expression program rather than a hidden extension-only state model;
- identity maps and import summaries remain staged artifacts under both `extensions/mlir_cse/` and `ir/stages/*/islands/mlir_cse/`.

### AIE package extension

The AIE extension proves that external toolchain-oriented backends can remain extension-owned without breaking the core compiler model.

### CPU reference backend

The CPU reference backend is intentionally small, but it matters architecturally. It compiles the same semantic state into a Python/NumPy reference package under `codegen/cpu_ref/` and participates in the same binding/build/run workflow.

That backend exists to prove a specific point: a reference execution backend can be added without inventing a new semantic model, a new frontend object graph, or a new artifact discipline.

## Rationale

The implemented rule is simple and important:
- semantics stay shared;
- artifacts stay explicit;
- backend-specific build/load/run policy lives in bindings/adapters;
- extension packages do not become the native semantic owner.

That is the current practical answer to retargetability.

## Coding pointers

Main code paths:
- `htp/backends/declarations.py`
- `htp/backends/pto/`
- `htp/bindings/pto.py`
- `htp/bindings/pto_runtime_adapter.py`
- `htp/backends/nvgpu/`
- `htp/ark/__init__.py`
- `htp/bindings/nvgpu.py`
- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp_ext/aie/`
- `htp/bindings/aie.py`
- `htp/bindings/aie_toolchain_adapter.py`
- `htp_ext/cpu_ref/`
- `htp/bindings/cpu_ref.py`
- `htp_ext/mlir_cse/`

## Current limits

The main remaining work is no longer missing backend substrate. Future work is about broader semantics, stronger automated development loops, and deeper performance exploration. Those tasks now live under the other broad TODO topics.
