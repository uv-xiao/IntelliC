# Layer 5 — Backends and Extensions

This layer describes how implemented targets and extensions consume the shared substrate.

## Narrative

HTP currently proves three backend families:
- PTO with real `a2a3sim` numerical execution
- NV-GPU with `.cu`-first emission and CUDA execution
- AIE as an extension-owned artifact, planning, build, and host-runtime path

The rule is consistent across them: core HTP owns semantics and artifacts; bindings and backend adapters own target-specific build/load/run policy.

Extensions participate through explicit seams. MLIR CSE is an implemented round-trip extension. AIE is an implemented backend/toolchain extension. Neither becomes the semantic owner of the compiler.

## Visual model

```text
shared semantics
   |        |         |
   v        v         v
 PTO      NVGPU      AIE(ext)
```

```text
core HTP -> emits package
binding  -> validate/build/load/run
adapter  -> real toolchain/runtime interaction
```

## Implemented contracts

- PTO prefers `3rdparty/pto-runtime/` and uses the real runtime adapter path
- NV-GPU owns `.cu` as the authoritative emitted source; compiled outputs are derived artifacts
- AIE remains extension-owned and emits MLIR-AIE sidecars plus build/run adapter outputs
- backend declarations are solver-visible and binding-visible

## Main code anchors

- `htp/backends/pto/`
- `htp/bindings/pto.py`
- `htp/bindings/pto_runtime_adapter.py`
- `htp/backends/nvgpu/`
- `htp/bindings/nvgpu.py`
- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp_ext/aie/`
- `htp/bindings/aie.py`
- `htp/bindings/aie_toolchain_adapter.py`
