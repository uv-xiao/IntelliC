# Example: PyPTO-Inspired PTO Vector Add

Code:

- `examples/pto/beginner/vector_add/demo.py`
- `examples/pto/beginner/vector_add/README.md`
- `examples/pto/beginner/vector_add/notebook.ipynb`

This example mirrors the shape of the `references/pypto` / `references/pto-runtime`
vector-add flow, but uses HTP’s artifact-first pipeline:

1. author the program through the public `htp.kernel` / `htp.routine`
   traced surface,
2. compile a small tile kernel to `pto-a2a3sim`,
3. replay the final Python stage in `sim`,
4. build the PTO package through the binding adapter,
5. execute the package through `pto-runtime` in `a2a3sim`.

The example is designed so replay always works. Package execution is also real
when the local PTO reference runtime is available under `3rdparty/pto-runtime/`
(or the compatibility fallback `references/pto-runtime/`): HTP marshals
`numpy.float32` input/output buffers plus the logical `size` scalar into the
`host_build_graph` ABI, and `a2a3sim` returns the numerically validated
`out = lhs + rhs` result.

Compared to the earlier dict-style example, the user now writes the kernel as a
plain Python function with argument annotations and an expression-form sink:
`store(out, lhs + rhs)`.
