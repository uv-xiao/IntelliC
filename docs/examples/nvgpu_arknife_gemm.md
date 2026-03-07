# Example: Arknife-Inspired NV-GPU GEMM Tile

Code:

- `examples/nvgpu_arknife_gemm/demo.py`
- `examples/nvgpu_arknife_gemm/README.md`
- `examples/nvgpu_arknife_gemm/notebook.ipynb`

This example turns the Arknife hardware-model story into concrete HTP code:

1. compile a block-level GEMM tile to `nvgpu-ampere`,
2. replay the final Python stage in `sim`,
3. run the package in `sim` with a registered replay kernel handler,
4. optionally build `.ptx` / `.cubin` with `nvcc` and launch the kernel on a
   CUDA device.

The device path is intentionally narrow in v1 but numerically real: it is a
source-first GEMM launch path with explicit tensor/scalar arguments, and on
machines with `nvcc` and a working CUDA driver it runs the real-device path
end-to-end.
