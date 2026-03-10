# WSP LittleKernel Pipelined GEMM

This example calibrates HTP's WSP schedule authoring against the
LittleKernel-style pipelined GEMM story while keeping the kernel body and the
workload readable as plain Python.

The example uses the fluent `@wsp.program(...)` builder and a double-buffered
mainloop body with implicit staged temporaries, but the more important change
is above the kernel body: the example now expresses prefetch, steady-state, and
writeback as separate workload tasks with explicit stage plans and dependency
edges.

Run:

```bash
python -m examples.wsp_littlekernel_pipelined_gemm.demo
```
