# TODO Layer 5 — Backends and Extensions

This layer tracks the remaining backend depth and extension breadth.

## Completion snapshot

- total checklist items: 10
- complete: 6
- partial: 3
- open: 1

## Detailed checklist

### PTO
- [x] Emit PTO packages through the shared artifact model.
- [x] Run real `a2a3sim` execution through the runtime adapter.
- [~] Broaden PTO beyond the current `a2a3sim`-anchored execution and package shape.

### NV-GPU
- [x] Emit `.cu`-first NV-GPU packages.
- [x] Run real CUDA execution from the emitted package.
- [~] Broaden NV-GPU lowering/runtime breadth, profiling, and Blackwell-specialized behavior.

### AIE and extensions
- [x] Support AIE planning, MLIR emission, build outputs, and host-runtime launch.
- [~] Deepen the AIE path beyond the current reference integration.
- [x] Support MLIR CSE as an extension-owned round-trip path.
- [ ] Add a next extension backend only if it strengthens the shared-substrate story.

## Why these tasks remain

The important point is that backend depth remains the issue, not the overall architecture. HTP already proves multi-backend participation. What remains is broader target coverage and more mature backend discharge paths.

## Coding pointers

Relevant anchors:
- `htp/backends/pto/`
- `htp/bindings/pto_runtime_adapter.py`
- `htp/backends/nvgpu/`
- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp_ext/aie/`
- `htp/bindings/aie_toolchain_adapter.py`
- `htp_ext/mlir_cse/`
