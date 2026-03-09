# Example: PyPTO-Calibrated PTO Vector DAG

Code:

- `examples/pto_pypto_vector_dag/demo.py`
- `examples/pto_pypto_vector_dag/README.md`

This example raises the public PTO story from a compact fused activation to a
larger arithmetic DAG inspired by `references/pypto/examples/language/intermediate/vector_dag.py`:

```python
summed = lhs + rhs
store(out, (summed + 1.0) * (summed + 2.0) + summed)
```

What it proves:

- traced kernels can express multi-step arithmetic DAGs as ordinary Python
  assignments and operators
- literal constants survive the semantic model, replay, and PTO fused-elementwise
  codegen path
- the example remains numerically real through PTO `a2a3sim`
