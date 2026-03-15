# WSP Warp GEMM Example

This example exercises the WSP authoring surface on top of the shared HTP
pipeline.

It proves three implemented contracts:

- WSP task graphs can now express producer, consumer, and epilogue roles as
  named workload tasks.
- each task can carry explicit stage-plan evidence such as `prologue`,
  `steady`, and `epilogue`.
- the kernel body uses explicit `shared_array(...)` storage plus
  `for ... in unroll(range(...))` loop annotations instead of raw scratch
  strings or manually duplicated stages.
- the default pipeline preserves those directives into staged `schedule.json`
  and `workload_ir.json`.

Run:

```bash
python -m examples.wsp_warp_gemm.demo
```
