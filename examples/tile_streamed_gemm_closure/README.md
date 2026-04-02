# Tile-Streamed GEMM Closure Proof

This example is the current human-facing proof surface for the AST-all-the-way
redesign on PR `#67`.

It shows one tile-streamed GEMM pipeline across four committed variants:

- `surface_program.py` — the surface-authored committed module
- `core_ir.py` — the normalized typed core IR module
- `scheduled_ir.py` — the tile-and-stage plus schedule/protocol enriched module
- `backend_ready_ir.py` — the backend-ready committed module

Each module exposes:

- `PROGRAM_MODULE`
- `program_module()`
- `run(...)`

The modules stay Python-owned and executable through `ProgramModule.run(...)`.
The example is intentionally explicit so reviewers can inspect the refactored
flow without digging through generated artifact directories.
