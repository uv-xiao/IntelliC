# WSP LittleKernel Pipelined GEMM

This example calibrates HTP's WSP schedule authoring against the
LittleKernel-style pipelined GEMM story while keeping the kernel body and the
schedule readable as plain Python.

The example uses the fluent `@wsp.program(...)` builder and a double-buffered
mainloop body so the public surface shows pipeline intent directly instead of
hiding it behind raw payload assembly.

Run:

```bash
python -m examples.wsp_littlekernel_pipelined_gemm.demo
```
