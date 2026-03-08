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

## Environment

The authoritative development environment is `pixi`.

- install and test with the default Python 3.11 environment: `pixi run verify`
- run tests on Python 3.10: `pixi run -e py310 test`
- run lint/hooks: `pixi run lint`

The fallback pip path remains supported for package consumers and simple local development:

- `python -m pip install -e '.[dev]'`

Runtime dependencies belong in `pyproject.toml` under `[project].dependencies`. Development-only tools belong in
`pixi.toml` and `[project.optional-dependencies].dev`. If examples, bindings, or runtime adapters import a package at
runtime, do not leave it as an implicit CI-only dependency.
