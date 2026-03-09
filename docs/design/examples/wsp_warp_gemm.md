# WSP Warp GEMM

Files:

- `examples/patterns/wsp/warp_tiled_gemm/demo.py`
- `examples/patterns/wsp/warp_tiled_gemm/README.md`

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
- The workload shape is visible as one CTA-level `2 x 2` tile grid:
  `tile_00`, `tile_01`, `tile_10`, and `tile_11`.
- Each task represents one warp-owned GEMM microtile, which is the simplest
  HTP equivalent of the warp-partitioned block structure seen in the Arknife
  reference.

Semantics:

- `A_row0` / `A_row1` are the two row-block tiles for the CTA.
- `B_col0` / `B_col1` are the two column-block tiles for the CTA.
- each WSP task owns one output subtile `C_ij`.
- `tile(block=(32, 64, 16))` and `num_warps=4` describe the block-level launch
  shape for the four independent warp tasks.

This is intentionally not modeled as fake `load/compute/store` phases. The
authored Python now says what the CTA actually owns.
