# Arknife-Inspired Blackwell Cluster GEMM

This example is the Blackwell counterpart to the Ampere mainloop example.

It demonstrates:

- explicit cluster-level authoring,
- `tma_load` and `tma_store`,
- `wgmma`,
- profile-specific hardware and channel metadata in emitted HTP artifacts.

Like the Ampere example, this surface does not introduce a separate tensor
class. The Arknife-specific memory/layout intent is attached to native HTP
kernel values.

Run it from the repo root:

```bash
python -m examples.nvgpu_arknife_blackwell.demo
```

This example is compile-and-replay focused. The current repository validates the
Blackwell codegen and stage artifacts locally, while real device execution still
depends on access to Blackwell-class hardware and a compatible CUDA stack.
