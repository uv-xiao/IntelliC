# WSP Warp GEMM Example

This example exercises the traced WSP authoring surface on top of the shared
HTP pipeline.

It proves three implemented contracts:

- WSP schedule directives are part of the user-facing program surface.
- The default pipeline preserves those directives into staged
  `schedule.json`.
- The final package remains replayable in `sim`.
- The authored Python shows named `load_warp`, `compute_warp`, and `store_warp`
  tasks instead of one anonymous metadata-wrapped call.

Run:

```bash
python -m examples.wsp_warp_gemm.demo
```
