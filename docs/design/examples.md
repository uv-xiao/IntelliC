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
3. inspect the staged `schedule.json` emitted from the shared pass spine

This example proves that WSP schedule directives are implemented frontend
surfaces, not only design notes.

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
