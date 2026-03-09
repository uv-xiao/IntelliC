# Example: Arknife-Inspired NV-GPU GEMM Tile

Code:

- `examples/nvgpu/arknife_gemm/demo.py`
- `examples/nvgpu/arknife_gemm/README.md`
- `examples/nvgpu/arknife_gemm/notebook.ipynb`

This example turns the Arknife hardware-model story into concrete HTP code:

1. author a GEMM routine through the public `htp.kernel` / `htp.routine`
   traced surface,
2. compile a block-level GEMM tile to `nvgpu-ampere`,
3. replay the final Python stage in `sim`,
4. run the package in `sim` with a registered replay kernel handler,
5. optionally build `.ptx` / `.cubin` with `nvcc` and launch the kernel on a
   CUDA device.

The device path is intentionally narrow in v1 but numerically real: it is a
source-first GEMM launch path with explicit tensor/scalar arguments, and on
machines with `nvcc` and a working CUDA driver it runs the real-device path
end-to-end.

The authoring goal here is human-first: the example now starts from a traced
Python `@kernel` definition and uses expression-form GEMM authoring
(`store(C, A @ B)`) rather than a hand-built nested payload.
