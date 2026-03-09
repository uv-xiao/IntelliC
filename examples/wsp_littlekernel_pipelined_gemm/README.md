# WSP LittleKernel Pipelined GEMM

This example calibrates HTP's WSP schedule authoring against the
LittleKernel-style pipelined GEMM story while keeping the kernel body and the
schedule readable as plain Python.

It now shows a visible prologue / steady-state / epilogue task structure in
the authored Python instead of a single metadata-wrapped kernel call.

Run:

```bash
python -m examples.wsp_littlekernel_pipelined_gemm.demo
```
