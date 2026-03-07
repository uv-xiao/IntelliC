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
4. execute the package through `pto-runtime` in `a2a3sim`.

The example is designed so replay always works. Package execution is also real
when the local PTO reference runtime is available under `3rdparty/pto-runtime/`
(or the compatibility fallback `references/pto-runtime/`), but the current v1 example is
an execution smoke test over the `host_build_graph` ABI rather than a full
tensor-marshaling numerical validation.
