# WSP Warp GEMM Example

This example exercises the WSP authoring surface on top of the shared HTP
pipeline.

It proves three implemented contracts:

- WSP task graphs can now express producer, consumer, and epilogue roles as
  named workload tasks.
- each task can carry explicit stage-plan evidence such as `prologue`,
  `steady`, and `epilogue`.
- the kernel body still uses typed temporaries instead of raw scratch-string
  plumbing.
- the default pipeline preserves those directives into staged `schedule.json`
  and `workload_ir.json`.

Run:

```bash
python -m examples.wsp_warp_gemm.demo
```
