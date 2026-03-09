# MLIR CSE Extension

This example exercises the MLIR round-trip extension with a tiny scalar kernel.

What it proves:

- the solver can select the `htp_ext.mlir_cse` extension path
- the extension emits MLIR-side evidence and reimports into the Python-first
  package layout
- replay still happens from the final HTP package in `sim`

Run:

```bash
python -m examples.extensions.mlir_cse.demo
```

Artifacts are written under `artifacts/extensions/mlir_cse/`.
