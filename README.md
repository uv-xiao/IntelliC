# HTP (Heterogeneous Tile Programming)

This repository contains both the HTP design material and a live Python implementation of the initial framework
substrate.

## Current implementation scope

Implemented today:

- staged artifact model and manifest writing
- pass contracts, pass manager, and pass trace
- non-trivial default pass semantics for canonicalization, type/layout/effect analysis, and schedule application
- replay/runtime surface with structured diagnostics
- binding API with PTO and NV-GPU bindings
- PTO backend artifact emission
- NV-GPU backend artifact emission with `.cu` as the primary source artifact
- normalized binding lifecycle results for `validate/build/load/run/replay`
- extension-owned MLIR CSE island example in `htp_ext/mlir_cse/`
- end-to-end compile entrypoint via `htp.compile_program(...)`

## Start here

- design: `docs/design/README.md`
- implementation: `htp/`
- tests: `tests/`
