# Example: LittleKernel-Calibrated WSP Pipelined GEMM

Code:

- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/README.md`

This example calibrates HTP's WSP public surface against the scheduling feel of
LittleKernel-style GEMM programs without giving up HTP's Python-first artifact
model.

What it proves:

- WSP examples no longer need a large top-level nested payload dict just to
  express one scheduled kernel
- kernel bodies stay in traced `@kernel` functions while the mainloop shape is
  expressed as a traced `@wsp.program(...)`
- the example now shows a visible prologue / steady-state / epilogue task
  structure instead of a single `store(C, A @ B)` wrapped by metadata
- replayed schedule artifacts remain explicit enough to inspect pipeline depth,
  warp allocation, and staged workload tasks
