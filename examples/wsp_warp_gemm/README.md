# WSP Warp GEMM Example

This example exercises the WSP authoring surface on top of the shared HTP
pipeline.

It proves three implemented contracts:

- WSP schedule directives are part of the user-facing program surface.
- The default pipeline preserves those directives into staged
  `schedule.json`.
- The final package remains replayable in `sim`.

Run:

```bash
python -m examples.wsp_warp_gemm.demo
```
