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

This example is intentionally a smoke path for runtime integration: it proves
the emitted PTO ABI and the build/run seam without yet implementing rich tensor
marshaling in the binding.

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

## Future examples

Design-only examples and roadmap material were moved to `docs/future/design/`.
