# WSP LittleKernel Pipelined GEMM

This example calibrates HTP's WSP schedule authoring against the
LittleKernel-style pipelined GEMM story while keeping the kernel body and the
workload readable as plain Python.

The example uses the fluent `@wsp.program(...)` builder and a double-buffered
mainloop body with explicit `shared_array(...)`, semantic loop indices from
`unroll(...)`, and Python tile views such as `A[:, k0:k0+16]` /
`B[k0:k0+16, :]` instead of repeated hand-written copy slots. The more
important change is above the kernel body: the example now expresses prefetch,
steady-state, and writeback as separate workload tasks with:

- `w.defaults(...)` for shared schedule context,
- `w.args.<name>` for bound kernel arguments,
- structured `prologue` / `steady` / `epilogue` step bodies instead of only
  string stage markers,
- explicit dependency edges between the task phases.

Run:

```bash
python -m examples.wsp_littlekernel_pipelined_gemm.demo
```
