# Example: PyPTO-Calibrated PTO GELU

Code:

- `examples/pto_pypto_gelu/demo.py`
- `examples/pto_pypto_gelu/README.md`

This example extends the PTO public surface beyond vector add and SwiGLU with a
reference-calibrated fast GELU:

```python
@kernel
def gelu(x: buffer(...), out: buffer(...), size: scalar(...)):
    store(out, x * sigmoid(x * 1.702))
```

What it proves:

- HTP now supports scalar-literal arithmetic inside traced kernels without
  pushing users back to raw payload assembly.
- PTO fused-elementwise lowering and `a2a3sim` execution handle literal-bearing
  expression DAGs, not only variable-to-variable elementwise chains.
- The public authoring surface remains plain Python even for a harder
  PyPTO-inspired activation path.
