# HTP Design → Code Map

This file is the bridge between `docs/design/` and the current implementation.

## Public entrypoints

- `htp/compiler.py` — `compile_program(...)`
- `htp/bindings/api.py` — `bind(...)`
- `htp/runtime/core.py` — replay runtime and kernel dispatch

## PTO path

- `htp/backends/pto/lower.py` — PTO codegen plan
- `htp/backends/pto/emit.py` — PTO artifact emission
- `htp/bindings/pto.py` — PTO validation / build / run / replay
- `htp/bindings/pto_runtime_adapter.py` — real `pto-runtime` integration, including
  `numpy` buffer/scalar marshaling for `a2a3sim`
- `3rdparty/pto-runtime/` — preferred external runtime checkout used by PTO execution

## NV-GPU path

- `htp/backends/nvgpu/lower.py` — NV-GPU codegen plan
- `htp/backends/nvgpu/emit.py` — `.cu`-first artifact emission
- `htp/bindings/nvgpu.py` — NV-GPU validation / build / run / replay
- `htp/bindings/nvgpu_cuda_adapter.py` — `nvcc` + CUDA-driver device path

## Examples

- `examples/pto_pypto_vector_add/demo.py` — PyPTO-inspired PTO example
- `examples/nvgpu_arknife_gemm/demo.py` — Arknife-inspired NV-GPU example
- `docs/examples/pto_pypto_vector_add.md` — PTO example walkthrough
- `docs/examples/nvgpu_arknife_gemm.md` — NV-GPU example walkthrough

## Contract tests

- `tests/backends/pto/`
- `tests/backends/nvgpu/`
- `tests/bindings/`
- `tests/golden/`
- `tests/examples/`
