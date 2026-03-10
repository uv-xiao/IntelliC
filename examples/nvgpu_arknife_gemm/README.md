# Arknife-Inspired Ampere GEMM Mainloop

This example is the concrete HTP counterpart of the Arknife Ampere CUDA
mainloop story:

- author the kernel with explicit block / warp / pipeline structure,
- express `cp_async`, `ldmatrix`, and `mma_sync` as first-class HTP operations,
- emit the instruction plan and hardware profile into the normal NV-GPU package,
- replay the final stage in `sim`,
- run the package in `sim`,
- optionally build and launch the generated CUDA package on Ampere-class GPUs.

The authoring surface stays inside HTP's native value model: `ark.tensor(...)`
is just the readable sugar for attaching Arknife memory/layout metadata to
ordinary HTP kernel values.

Run it from the repo root:

```bash
python -m examples.nvgpu_arknife_gemm.demo
```

The example writes outputs under `artifacts/nvgpu_arknife_gemm/`.

Notes:

- the `sim` path is deterministic and does not need CUDA;
- replay now uses reference semantics for the staged `cp_async`, `ldmatrix`,
  `mma_sync`, and `commit` intrinsic flow instead of falling back to
  unsupported-intrinsic stubs;
- the emitted `.cu` source preserves the Arknife instruction plan as annotated
  metadata and comments, while using a numerically-correct fallback kernel body;
- the device path needs `nvcc`, a CUDA driver, and a GPU visible to the
  process;
- on A100-class machines with the required CUDA stack, the current example is
  expected to complete the real-device path end-to-end.
