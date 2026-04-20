# WSP LittleKernel Pipelined GEMM

This example calibrates HTP's WSP schedule authoring against the
LittleKernel-style pipelined GEMM story while keeping the kernel body and the
workload readable as plain Python.

The example uses nested `@w.task(...)` / `@w.mainloop(...)` functions and a
double-buffered mainloop body with explicit `shared_array(...)`, semantic loop
indices from `unroll(...)`, and Python tile views such as `A[:, k0:k0+16]` /
`B[k0:k0+16, :]` instead of repeated hand-written copy slots. The more
important change is above the kernel body: the example now expresses prefetch,
steady-state, and writeback as separate workload tasks with:

- task decorators for schedule context,
- `w.args.<name>` for bound kernel arguments,
- structured `with w.prologue():`, `with w.steady():`, and
  `with w.epilogue():` bodies with operation calls such as `w.cp_async(...)`
  and `w.mma_sync(...)`,
- explicit dependency edges between the task phases,
- and an explicit `epilogue_tiles` phase before final writeback so the example
  reads more like a real staged mainloop than a two-step sketch.

Run:

```bash
python -m examples.wsp_littlekernel_pipelined_gemm.demo
```
