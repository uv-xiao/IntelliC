# Impl: AIE Extension Backend

Current code anchors:

- extension emitter: `htp_ext/aie/emit.py`
- binding: `htp/bindings/aie.py`
- binding selection: `htp/bindings/api.py`
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
- `extensions.aie.toolchain_contract`
- `extensions.aie.mlir`
- `extensions.aie.sidecars.*`
- `extensions.aie.runtime_contract`

Current scope:

- extension-owned emission only
- replay stays in Python `sim`
- no device toolchain execution yet
