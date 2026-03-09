# Example: LittleKernel-Calibrated WSP Pipelined GEMM

Code:

- `examples/patterns/wsp/littlekernel_mainloop_gemm/demo.py`
- `examples/patterns/wsp/littlekernel_mainloop_gemm/README.md`

This example calibrates HTP's WSP public surface against the scheduling feel of
LittleKernel-style GEMM programs without giving up HTP's Python-first artifact
model.

What it proves:

- WSP examples no longer need a large top-level nested payload dict just to
  express one scheduled kernel
- kernel bodies stay in traced `@kernel` functions while the mainloop shape is
  expressed as a traced `@wsp.program(...)`
- the example now shows a CTA-owned `4 x 2` output-tile lattice instead of a
  fake prologue / steady-state / epilogue chain
- replayed schedule artifacts remain explicit enough to inspect pipeline depth,
  warp allocation, and staged workload tasks

Semantics:

- the program describes one CTA computing eight output tiles:
  `tile_m0n0` through `tile_m3n1`
- the schedule carries the LittleKernel-inspired part:
  - block tile `(128, 256, 64)`
  - software-pipeline depth `3`
  - `num_warps = 8`
- the task graph is intentionally flat because the main semantic content is
  ownership plus schedule, not an invented sequence of phases

This mirrors the references more honestly. LittleKernel’s key story is not
“name three phases”; it is “make tile ownership, warp allocation, and
mainloop pipeline depth explicit in the authored program”.
