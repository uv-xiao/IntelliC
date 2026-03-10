# TODO — Backends and Extensions

This document records the backend-depth topic that is now implemented.

## Completion snapshot

- total checklist items: 11
- complete: 11
- partial: 0
- open: 0

## Detailed checklist

### PTO
- [x] Emit PTO packages through the shared artifact model.
- [x] Run real `a2a3sim` execution through the runtime adapter.
- [x] Broaden PTO beyond the current `a2a3sim`-anchored execution and package shape.

### NV-GPU
- [x] Emit `.cu`-first NV-GPU packages.
- [x] Run real CUDA execution from the emitted package.
- [x] Integrate Arknife-style hardware, channel, and instruction plans into the native NV-GPU path.
- [x] Broaden NV-GPU lowering/runtime breadth, profiling, and deeper Blackwell-specialized behavior beyond the current Arknife-backed profile plan.

### AIE and extensions
- [x] Support AIE planning, MLIR emission, build outputs, and host-runtime launch.
- [x] Deepen the AIE path beyond the current reference integration.
- [x] Support MLIR CSE as an extension-owned round-trip path.
- [x] Add a next extension backend only if it strengthens the shared-substrate story.

## What landed

The important point is that backend depth was closed without changing the architecture:
- PTO now carries explicit `a2a3sim` and `a2a3` package/runtime contracts.
- NV-GPU now emits profile-specialized plans, build flags, and runtime perf records for Ampere and Blackwell.
- AIE now emits richer build outputs, launch plans, and perf sidecars.
- `cpu_ref` now exists as a lightweight host reference backend that reuses the same shared semantic substrate instead of introducing a second compiler path.

## Coding pointers

Relevant anchors:
- `htp/backends/pto/`
- `htp/bindings/pto_runtime_adapter.py`
- `htp/backends/nvgpu/`
- `htp/ark/__init__.py`
- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp_ext/aie/`
- `htp/bindings/aie_toolchain_adapter.py`
- `htp_ext/cpu_ref/`
- `htp/bindings/cpu_ref.py`
- `htp_ext/mlir_cse/`

## Remaining status

This topic no longer carries an open standalone TODO. Future backend work now belongs to broader semantic/performance exploration rather than a missing retargetable backend substrate.
