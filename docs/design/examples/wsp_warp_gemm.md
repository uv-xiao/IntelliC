# WSP Warp GEMM

Files:

- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_warp_gemm/README.md`

This example uses the implemented `htp.wsp` authoring surface to compile a
warp-specialized matmul workload with explicit schedule directives and staged
task boundaries.

What it proves:

- WSP schedule directives survive canonicalization and semantic-model
  construction.
- The pass spine emits staged `warp_role_plan.json` and `pipeline_plan.json`
  analyses before applying them into final `schedule.json`.
- The final package remains replayable in `sim`.
- The public WSP example no longer needs a nested top-level raw payload dict;
  it is authored through traced `@kernel` and `@wsp.program(...)` surfaces.
- The workload shape is now visible in authored Python through named
  `load_warp`, `compute_warp`, and `store_warp` tasks instead of a single
  anonymous kernel call wrapped in metadata.
