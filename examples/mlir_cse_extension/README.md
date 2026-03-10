# MLIR CSE Extension Example

This example demonstrates HTP's extension-owned MLIR round-trip path on a
non-trivial scalar expression chain.

The example deliberately uses a repeated-value arithmetic DAG:

- `sum0 = x + y`
- `delta0 = x - y`
- `out = sum0 * delta0`

That gives the extension a meaningful canonical elementwise slice to export,
run through the MLIR CSE pipeline, import back into Python-space artifacts, and
replay in `sim`.

Run:

```bash
python -m examples.mlir_cse_extension.demo
```
