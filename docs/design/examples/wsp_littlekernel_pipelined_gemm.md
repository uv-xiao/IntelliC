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
- kernel bodies can stay in traced `@kernel` functions while schedule evidence
  is expressed through named WSP helpers such as `task(...)`, `tile(...)`,
  `pipeline(...)`, and `resources(...)`
- replayed schedule artifacts remain explicit enough to inspect pipeline depth
  and warp allocation
