# Example: PyPTO-Calibrated PTO SwiGLU

Code:

- `examples/pto/intermediate/swiglu/demo.py`
- `examples/pto/intermediate/swiglu/README.md`

This example raises the PTO flagship bar above vector add while keeping the
authoring surface Python-native. The user writes a traced `@kernel`
definition:

```python
@kernel
def swiglu(gate: buffer(...), up: buffer(...), out: buffer(...), size: scalar(...)):
    gate_sigmoid = sigmoid(gate)
    store(out, gate * gate_sigmoid * up)
```

What it proves:

- HTP’s public surface can express a non-trivial fused activation without raw
  program dicts or constructor stacks.
- The compiler now stages richer unary/binary elementwise semantics into the
  shared semantic payload and lowers them as one fused backend kernel.
- PTO `a2a3sim` execution is numerically real for this harder case, not only
  for compact smoke kernels.
- PTO runs remain stable even when multiple different PTO packages execute in
  one Python process; the binding isolates runtime execution to avoid
  orchestration-plugin collisions in `pto-runtime`.

Artifacts to inspect after compilation:

- `codegen/pto/pto_codegen.json`
- `codegen/pto/kernels/aiv/swiglu.cpp`
- `codegen/pto/orchestration/swiglu_orchestration.cpp`
- `ir/stages/<id>/kernel_ir.json`
- `ir/stages/<id>/types.json`
- `ir/stages/<id>/layout.json`
