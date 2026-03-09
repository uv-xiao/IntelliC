# Arknife-Inspired NV-GPU GEMM Tile

This example is the concrete HTP counterpart of the Arknife-style explicit
hardware abstraction story:

- compile a block-level GEMM tile to the `nvgpu` backend,
- replay the final Python stage in `sim`,
- run the package in `sim` with a registered kernel handler,
- optionally materialize `.ptx` / `.cubin` and launch the GEMM kernel with real
  tensor and shape arguments
  on a CUDA device.

Run it from the repo root:

```bash
python -m examples.nvgpu.arknife_gemm.demo
```

The example writes outputs under `artifacts/nvgpu_arknife_gemm/`.

Notes:

- the `sim` path is deterministic and does not need CUDA;
- the device path needs `nvcc`, a CUDA driver, and a GPU visible to the
  process;
- on A100-class machines with the required CUDA stack, the current example is
  expected to complete the real-device path end-to-end.
