# HTP Design → Code Map

This file is the bridge between `docs/design/` and the current implementation.

## Public entrypoints

- `htp/compiler.py` — `compile_program(...)`
- `htp/bindings/api.py` — `bind(...)`
- `htp/runtime/core.py` — replay runtime and kernel dispatch
- `htp/solver.py` — capability solver and final artifact checks
- `htp/diagnostics.py` — diagnostic catalog and fix-hint policies
- `htp/tools.py` / `htp/__main__.py` — replay / verify / semantic diff / explain

## PTO path

- `htp/backends/pto/declarations.py` — solver-visible PTO capability and artifact declarations
- `htp/backends/pto/lower.py` — PTO codegen plan
- `htp/backends/pto/emit.py` — PTO artifact emission
- `htp/bindings/pto.py` — PTO validation / build / run / replay
- `htp/bindings/pto_runtime_adapter.py` — real `pto-runtime` integration, including
  `numpy` buffer/scalar marshaling for `a2a3sim`
- `3rdparty/pto-runtime/` — preferred external runtime checkout used by PTO execution

## NV-GPU path

- `htp/backends/nvgpu/declarations.py` — solver-visible NV-GPU capability and artifact declarations
- `htp/backends/nvgpu/lower.py` — NV-GPU codegen plan
- `htp/backends/nvgpu/emit.py` — `.cu`-first artifact emission
- `htp/bindings/nvgpu.py` — NV-GPU validation / build / run / replay
- `htp/bindings/nvgpu_cuda_adapter.py` — `nvcc` + CUDA-driver device path

## Semantic substrate

- `htp/passes/program_model.py` — canonicalization, semantic model, type/layout/effect synthesis
- `htp/ir/op_specs.py` — centralized op semantics for effects / phase / latency
- `htp/passes/manager.py` — stage emission, analyses, islands

## Extensions

- `htp_ext/mlir_cse/` — MLIR CSE round-trip extension
- `htp_ext/aie/emit.py` — AIE artifact emission extension
- `htp/bindings/aie.py` — AIE package validation and replay binding

## Examples

- `examples/pto_pypto_vector_add/demo.py` — PyPTO-inspired PTO example
- `examples/nvgpu_arknife_gemm/demo.py` — Arknife-inspired NV-GPU example
- `tests/extensions/test_aie_backend.py` — AIE extension validation example
- `docs/examples/pto_pypto_vector_add.md` — PTO example walkthrough
- `docs/examples/nvgpu_arknife_gemm.md` — NV-GPU example walkthrough

## Contract tests

- `tests/backends/pto/`
- `tests/backends/nvgpu/`
- `tests/bindings/`
- `tests/golden/`
- `tests/examples/`
