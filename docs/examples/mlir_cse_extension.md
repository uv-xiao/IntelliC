# MLIR CSE Extension Example

Code anchor: `examples/mlir_cse_extension/demo.py`

This example demonstrates:

- a requested extension surface (`extensions.requested = ["htp_ext.mlir_cse"]`)
- solver-visible template selection for the MLIR CSE path
- an emitted extension package with MLIR artifacts and replayable staged Python

It is intentionally narrow: it proves extension composition and emitted island
artifacts, not backend code generation.
