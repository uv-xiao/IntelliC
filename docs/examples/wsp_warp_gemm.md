# WSP Warp GEMM

Files:

- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_warp_gemm/README.md`

This example uses the implemented `htp.wsp` authoring surface to compile a
matmul-style kernel with explicit schedule directives.

What it proves:

- WSP schedule directives survive canonicalization and semantic-model
  construction.
- The typed schedule plan records warp-oriented launch and pipeline directives
  in staged `schedule.json`.
- The final package remains replayable in `sim`.
