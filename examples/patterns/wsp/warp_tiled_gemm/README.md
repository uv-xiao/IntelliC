# WSP Warp GEMM Example

This example exercises the traced WSP authoring surface on top of the shared
HTP pipeline.

It proves three implemented contracts:

- WSP schedule directives are part of the user-facing program surface.
- The default pipeline preserves those directives into staged
  `schedule.json`.
- The final package remains replayable in `sim`.
- The authored Python exposes the actual block ownership story: one CTA owns a
  `2 x 2` output-tile grid and each warp task owns one microtile.

The key tasks are:

- `tile_00`
- `tile_01`
- `tile_10`
- `tile_11`

This is meant to be the HTP equivalent of the warp-partitioned tile ownership
you see in the Arknife GEMM references, not a fake load/compute/store phase
chain.

Run:

```bash
python -m examples.patterns.wsp.warp_tiled_gemm.demo
```
