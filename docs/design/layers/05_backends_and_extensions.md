# Layer 5 — Backends and Extensions

This layer describes how implemented targets and extension packages consume the shared compiler substrate.

## Why this layer exists

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

This is the current proof that HTP can own the source artifact while delegating execution policy to the binding/adapter layer.

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
- `htp/bindings/nvgpu.py`
- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp_ext/aie/`
- `htp/bindings/aie.py`
- `htp/bindings/aie_toolchain_adapter.py`
- `htp_ext/mlir_cse/`

## Current limits

Backend and extension participation are real, but broader target depth still remains. Those missing tasks now live in `docs/todo/layers/05_backends_and_extensions.md`.
