# WSP Warp GEMM Example

This example exercises the WSP authoring surface on top of the shared HTP
pipeline.

It proves three implemented contracts:

- WSP task graphs can now express producer, consumer, and epilogue roles as
  named workload tasks.
- each task can carry explicit stage-plan evidence such as `prologue`,
  `steady`, and `epilogue`, now emitted as structured step objects instead of
  only string markers.
- the workload uses `w.defaults(...)` and `w.args.<name>` so repeated schedule
  facts and kernel-argument wiring stay concise and native.
- the workload is now a four-task pipeline (`load`, `mma`, `accumulate`,
  `store`) instead of a minimal producer/consumer sketch.
- the kernel body uses explicit `shared_array(...)` storage, semantic loop
  indices from `unroll(...)`, and Python slice views such as
  `A[:, k0:k0+16]` / `B[k0:k0+16, :]` instead of raw scratch strings or
  manually duplicated stages.
- the default pipeline preserves those directives into staged
  `state.json#/aspects/schedule` and `state.json#/items/workload_ir`.

Run:

```bash
python -m examples.wsp_warp_gemm.demo
```
