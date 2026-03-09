# WSP LittleKernel Pipelined GEMM

This example calibrates HTP's WSP schedule authoring against the
LittleKernel-style pipelined GEMM story while keeping the kernel body and the
schedule readable as plain Python.

It now models the thing that matters in the LittleKernel references:

- one CTA-level output-tile lattice
- a deeper software-pipeline directive
- explicit warp allocation

The authored Python therefore names the output tiles directly:

- `tile_m0n0` through `tile_m3n1`

instead of pretending the mainloop is best explained as a fake prologue /
steady-state / epilogue task chain.

Run:

```bash
python -m examples.patterns.wsp.littlekernel_mainloop_gemm.demo
```
