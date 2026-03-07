# Example: PyPTO-Inspired PTO Vector Add

Code:

- `examples/pto_pypto_vector_add/demo.py`
- `examples/pto_pypto_vector_add/README.md`
- `examples/pto_pypto_vector_add/notebook.ipynb`

This example mirrors the shape of the `references/pypto` / `references/pto-runtime`
vector-add flow, but uses HTP’s artifact-first pipeline:

1. compile a small tile kernel to `pto-a2a3sim`,
2. replay the final Python stage in `sim`,
3. build the PTO package through the binding adapter,
4. attempt package execution through `pto-runtime`.

The example is designed so replay always works. Build and package execution
depend on the local PTO toolchain environment.
