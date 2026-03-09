# WSP Warp GEMM

Files:

- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_warp_gemm/README.md`

This example uses the implemented `htp.wsp` authoring surface to compile a
matmul-style kernel with explicit schedule directives.

What it proves:

- WSP schedule directives survive canonicalization and semantic-model
  construction.
- The pass spine emits staged `warp_role_plan.json` and `pipeline_plan.json`
  analyses before applying them into final `schedule.json`.
- The final package remains replayable in `sim`.
- The public WSP example no longer needs a nested top-level raw payload dict;
  it is authored through a traced `@kernel` plus `htp.wsp.task(...)`,
  `htp.wsp.tile(...)`, and related helper surfaces.
