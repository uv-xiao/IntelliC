# Impl: AIE Extension Backend

Current code anchors:

- solver-visible declaration: `htp_ext/aie/declarations.py`
- planning analyses: `htp_ext/aie/plan.py`
- extension emitter: `htp_ext/aie/emit.py`
- binding: `htp/bindings/aie.py`
- binding selection: `htp/bindings/api.py`
- compile target entrypoint: `htp/compiler.py`
- tests: `tests/extensions/test_aie_backend.py`

Implemented artifact contract:

- `codegen/aie/aie.mlir`
- `codegen/aie/mapping.json`
- `codegen/aie/fifos.json`
- `codegen/aie/host.py`
- `codegen/aie/aie_codegen.json`
- `codegen/aie/toolchain.json`

Manifest surface:

- `target.backend = "aie"`
- `target.variant = "mlir-aie"`
- `outputs.aie_codegen_index`
- `outputs.toolchain_manifest`
- `extensions.aie.toolchain_contract`
- `extensions.aie.mlir`
- `extensions.aie.toolchain_manifest`
- `extensions.aie.sidecars.*`
- `extensions.aie.runtime_contract`

Implemented solver/runtime scope:

- AIE now has solver-visible target capabilities and artifact requirements through
  `htp_ext/aie/declarations.py`
- `htp.compile_program(..., target="aie-<profile>")` emits AIE packages while preserving
  the canonical staged replay graph
- AIE mapping and FIFO planning are now explicit analyses emitted under
  `ir/stages/s01/analysis/`
- emitted `aie.mlir`, `mapping.json`, and `fifos.json` are derived from those
  explicit plans rather than placeholder-only comments

Current scope:

- extension-owned planning + emission
- replay stays in Python `sim`
- no device toolchain execution yet
