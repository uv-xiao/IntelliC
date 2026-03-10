# Backends and Extensions

This document describes how implemented targets and extension packages consume the shared compiler substrate.

## Why this topic exists

HTP is trying to support multiple hardware targets without letting each backend become a separate compiler architecture. The implemented repository already proves that this is practical at a meaningful scale:
- PTO runs through a real runtime adapter path
- NV-GPU runs through a real CUDA path from emitted `.cu`
- AIE exists as an extension-owned toolchain path
- MLIR CSE exists as an extension-owned round-trip path

The rule across all of them is consistent: core HTP owns semantics and artifacts; backends and extensions consume those contracts.

## Visual model

```text
shared semantics and staged artifacts
        |          |           |
        v          v           v
       PTO       NVGPU      AIE(ext)
                     \
                      \-> MLIR CSE(ext round-trip)
```

## Implemented backend inventory

### PTO

Implemented today:
- PTO lowerer and emitter
- binding lifecycle support
- real `pto-runtime` integration
- numerical `a2a3sim` example path

The current example demonstrates a true build/run path, not only package emission.

### NV-GPU

Implemented today:
- `.cu`-first artifact ownership
- NV-GPU lowerer and emitter
- CUDA adapter with real build/launch path
- GEMM example with real CUDA execution
- explicit Arknife-style hardware/profile metadata in codegen artifacts
- explicit Arknife-style instruction-plan metadata for Ampere and Blackwell

This is the current proof that HTP can own the source artifact while delegating execution policy to the binding/adapter layer.

#### Arknife integration inside NV-GPU

The important new point is that Arknife-style targeting is now implemented as a
native HTP path, not a disconnected example convention.

What is real today:

- Ampere and Blackwell remain profiles of the same `nvgpu` backend.
- `htp.ark` programs lower into the standard HTP program model.
- `htp.ark` no longer owns a separate tensor class; it attaches Arknife
  memory-space and axis-layout metadata to native `htp.kernel.KernelValue`
  objects.
- the NV-GPU lowerer inspects the `ark` sidecar and validates profile /
  capability compatibility.
- the emitted `nvgpu_codegen.json` now carries:
  - the hardware profile summary,
  - the channel plan,
  - and the per-kernel instruction plan.
- the emitted `.cu` source keeps those instruction decisions visible as
  annotated comments while preserving a numerically-correct fallback kernel body.

That is an important architectural step. It means explicit hardware and
instruction planning now exist as first-class compiler facts inside HTP’s
backend contracts instead of living only in reference notes.

### AIE extension backend

Implemented today:
- AIE planning analysis sidecars
- AIE MLIR artifact emission
- reference toolchain build outputs
- host-runtime launch path through the binding-owned adapter

This is important because it proves that extension-owned backends can still participate in the same artifact and workflow discipline.

## Implemented extension inventory

### MLIR CSE

The MLIR CSE extension proves that HTP can run an extension-owned round-trip path while preserving stage discipline, artifact evidence, and identity/mapping behavior.

What is implemented today:

- extension-owned export/import passes participate in the normal solver and pass-trace flow
- the extension can now round-trip the broader scalar integer elementwise subset:
  - `add`
  - `sub`
  - `mul`
  - `div`
- replay uses the imported expression program rather than a hidden extension-only state model
- identity maps and import summaries remain staged artifacts under both `extensions/mlir_cse/` and `ir/stages/*/islands/mlir_cse/`

### AIE package extension

The AIE extension proves that external toolchain-oriented backends can remain extension-owned without breaking the core compiler model.

## Rationale

The implemented rule is simple and important:
- semantics stay shared,
- artifacts stay explicit,
- backend-specific build/load/run policy lives in bindings/adapters,
- and extension packages do not become the native semantic owner.

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
- `htp_ext/mlir_cse/`

## Current limits

Backend and extension participation are real, but broader target depth still
remains. The main remaining work is no longer “does HTP support Arknife-style
backend planning at all?” That part is now implemented. The remaining gap is
deeper profile-specialized lowering, wider runtime breadth, and additional
extension backends. Those tasks now live in
`docs/todo/backends_and_extensions.md`.
