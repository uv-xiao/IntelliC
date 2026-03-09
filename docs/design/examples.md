# HTP Examples — Implemented Flows

This file only documents the examples that run against the current
implementation.

## PTO example

Files:

- `examples/pto_pypto_vector_add/demo.py`
- `examples/pto_pypto_vector_add/notebook.ipynb`
- `docs/examples/pto_pypto_vector_add.md`

Flow:

1. compile a PTO package for `pto-a2a3sim`
2. replay the latest staged Python program in `sim`
3. build the PTO package through the binding adapter
4. run the package through the real `pto-runtime` `host_build_graph` simulation path

This example is now a real numerical path: the binding marshals
`numpy.float32` input/output buffers and the logical `size` scalar into the
`host_build_graph` ABI, and `a2a3sim` returns the validated vector-add output.

## NV-GPU example

Files:

- `examples/nvgpu_arknife_gemm/demo.py`
- `examples/nvgpu_arknife_gemm/notebook.ipynb`
- `docs/examples/nvgpu_arknife_gemm.md`

Flow:

1. compile an NV-GPU package for the Ampere profile
2. replay the latest staged Python program in `sim`
3. run the package in `sim` with a registered replay kernel handler
4. build `.ptx` and `.cubin` from the authoritative `.cu`
5. launch the kernel through the CUDA driver adapter on a real device

## WSP example

Files:

- `examples/wsp_warp_gemm/demo.py`
- `docs/examples/wsp_warp_gemm.md`

Flow:

1. compile an NV-GPU package from the `htp.wsp` authoring surface
2. replay the latest staged Python program in `sim`
3. inspect the staged `schedule.json`, `analysis/warp_role_plan.json`, and
   `analysis/pipeline_plan.json` emitted from the shared pass spine

This example proves that WSP schedule directives are implemented frontend
surfaces, and that warp/pipeline planning is implemented as staged passes.

## CSP example

Files:

- `examples/csp_channel_pipeline/demo.py`
- `docs/examples/csp_channel_pipeline.md`

Flow:

1. compile an NV-GPU package from the `htp.csp` authoring surface
2. replay the latest staged Python program in `sim`
3. inspect the staged `effects.json` protocol obligations

This example proves that CSP process/channel metadata lowers into typed effect
state in the implemented compiler.

## AIE example

Files:

- `examples/aie_channel_pipeline/demo.py`
- `docs/examples/aie_channel_pipeline.md`

Flow:

1. compile an AIE package from the `htp.csp` authoring surface
2. replay the latest staged Python program in `sim`
3. inspect staged AIE analyses under
   `ir/stages/s01/analysis/aie_mapping_plan.json` and
   `ir/stages/s01/analysis/aie_fifo_plan.json`
4. inspect emitted `codegen/aie/aie.mlir`, `mapping.json`, and `fifos.json`

This example proves that the AIE extension now splits planning from emission,
and that the emitted MLIR/sidecars derive from explicit mapping/FIFO plans.

## MLIR CSE extension example

Files:

- `examples/mlir_cse_extension/demo.py`
- `docs/examples/mlir_cse_extension.md`

Flow:

1. solve a program with `extensions.requested = ["htp_ext.mlir_cse"]`
2. show that the solver selects `htp.default+htp_ext.mlir_cse.v1`
3. emit the MLIR CSE extension package and replay the latest stage in `sim`

This example proves the extension-composition story is implemented as a
solver-visible template choice, not only a design claim.

## Serving routine example

Files:

- `examples/serving_routine/demo.py`
- `docs/examples/serving_routine.md`

Flow:

1. compile a workload-level serving routine with multiple tasks and
   dependencies
2. replay the latest staged Python program in `sim`
3. inspect `workload_ir.json` as the routine-level contract

This example proves the repo now includes a workload-level routine example
above the kernel-only examples.

## Future examples

Design-only examples and roadmap material were moved to `docs/future/`.

## Tooling surface

The implemented package-level tooling is now:

1. `htp replay <package>`
2. `htp verify <package>`
3. `htp diff --semantic <left> <right>`
4. `htp explain <diagnostic-code>`

These commands are thin wrappers over `htp/tools.py` and operate on emitted
artifact packages rather than hidden compiler state.
