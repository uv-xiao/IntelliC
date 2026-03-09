# HTP Design → Code Map

This file is the bridge between `docs/design/` and the current implementation.

## Public entrypoints

- `htp/compiler.py` — `compile_program(...)`
- `htp/bindings/api.py` — `bind(...)`
- `htp/runtime/core.py` — replay runtime and kernel/intrinsic dispatch
- `htp/solver.py` — capability solver and final artifact checks
- `htp_ext/registry.py` — extension registration for solver / pass / template discovery
- `htp/diagnostics.py` — diagnostic catalog and fix-hint policies
- `htp/agent_policy.py` — agent policy loading for verify/promote tooling
- `htp/perf.py` — perf metric loading and baseline-threshold comparison
- `htp/bindings/validate.py` — generic manifest/artifact validation, including optional manifest section shape checks
- `htp/intrinsics.py` — intrinsic declarations plus lower/emit/sim handler registration
- `htp_ext/aie/intrinsics.py` — extension-owned backend intrinsic package example
- `htp/pipeline/defaults.py` — default pipeline execution over solver-validated pass contracts
- `htp/tools.py` / `htp/__main__.py` — replay / verify / promote-plan / semantic diff / explain

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

- `htp/ir/layout.py` — facet-product layout payload helpers
- `htp/ir/types.py` — structured dtype / index / shape / value-kind payloads
- `htp/ir/semantics.py` — staged kernel/workload semantic dataclasses
- `htp/passes/program_model.py` — canonicalization, semantic model, type/layout/effect synthesis
- `htp/passes/analyze_warp_specialization.py` — staged warp-role planning analysis
- `htp/passes/apply_warp_specialization.py` — applied warp-role schedule transform
- `htp/passes/analyze_software_pipeline.py` — staged software-pipeline analysis
- `htp/passes/apply_software_pipeline.py` — applied software-pipeline schedule transform
- `htp/passes/registry.py` — registered core and extension pass surface
- `htp/pipeline/registry.py` — registered pipeline template surface
- `htp/ir/op_specs.py` — centralized op semantics for effects / phase / latency
- `htp/passes/manager.py` — stage emission, analyses, islands
- `htp/passes/trace.py` — normalized pass-trace events including `requires_satisfied`

## Programming surfaces

- `htp/wsp/__init__.py` — workload/schedule authoring helpers and lowering surface
- `htp/csp/__init__.py` — process/channel authoring helpers and lowering surface

## Extensions

- `htp_ext/mlir_cse/` — MLIR CSE round-trip extension, including registered export/import passes and identity maps
- `htp_ext/aie/emit.py` — AIE artifact emission extension
- `htp/bindings/aie.py` — AIE package validation and replay binding

## Examples

- `examples/pto_pypto_vector_add/demo.py` — PyPTO-inspired PTO example
- `examples/nvgpu_arknife_gemm/demo.py` — Arknife-inspired NV-GPU example
- `examples/wsp_warp_gemm/demo.py` — WSP frontend example with staged schedule directives
- `examples/csp_channel_pipeline/demo.py` — CSP frontend example with typed protocol effects
- `tests/extensions/test_aie_backend.py` — AIE extension validation example
- `docs/examples/pto_pypto_vector_add.md` — PTO example walkthrough
- `docs/examples/nvgpu_arknife_gemm.md` — NV-GPU example walkthrough
- `docs/examples/wsp_warp_gemm.md` — WSP example walkthrough
- `docs/examples/csp_channel_pipeline.md` — CSP example walkthrough

## Contract tests

- `tests/backends/pto/`
- `tests/backends/nvgpu/`
- `tests/bindings/`
- `tests/golden/`
- `tests/examples/`
