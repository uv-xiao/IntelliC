# WSP LittleKernel Pipelined GEMM

This example calibrates HTP's WSP schedule authoring against the
LittleKernel-style pipelined GEMM story while keeping the kernel body and the
schedule readable as plain Python.

The example uses the fluent `@wsp.program(...)` builder and a double-buffered
mainloop body with implicit staged temporaries so the public surface shows
pipeline intent directly instead of hiding it behind raw payload assembly or
string-named scratch buffers.

Run:

```bash
python -m examples.wsp_littlekernel_pipelined_gemm.demo
```
