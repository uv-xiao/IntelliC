# Implemented Example Docs

These files explain runnable, code-backed examples in `examples/`.

Current example tree:

- `examples/pto/`
  - `docs/design/examples/pto_pypto_vector_add.md`
  - `docs/design/examples/pto_pypto_swiglu.md`
  - `docs/design/examples/pto_pypto_gelu.md`
  - `docs/design/examples/pto_pypto_vector_dag.md`
- `examples/nvgpu/`
  - `docs/design/examples/nvgpu_arknife_gemm.md`
- `examples/patterns/wsp/`
  - `docs/design/examples/wsp_warp_gemm.md`
  - `docs/design/examples/wsp_littlekernel_pipelined_gemm.md`
- `examples/patterns/csp/`
  - `docs/design/examples/csp_channel_pipeline.md`
- `examples/extensions/`
  - `docs/design/examples/aie_channel_pipeline.md`
  - `docs/design/examples/mlir_cse_extension.md`
- `examples/workloads/`
  - `docs/design/examples/serving_routine.md`

The pattern examples are the main proof that HTP’s public surfaces can express
schedule and protocol intent directly in Python, rather than falling back to
payload-shaped demo programs.

The corresponding runnable code lives under `examples/`.
