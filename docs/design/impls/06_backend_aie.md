# Impl: AIE Extension Backend

Current code anchors:

- solver-visible declaration: `htp_ext/aie/declarations.py`
- planning analyses: `htp_ext/aie/plan.py`
- extension emitter: `htp_ext/aie/emit.py`
- reference toolchain shim: `htp_ext/aie/toolchain.py`
- binding: `htp/bindings/aie.py`
- adapter: `htp/bindings/aie_toolchain_adapter.py`
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
- `build(mode="device")` now executes the reference AIE toolchain shim and
  materializes:
  - `build/aie/build_product.json`
  - `build/aie/host_runtime.json`
- `load(mode="device").run(...)` now goes through emitted `codegen/aie/host.py`
  plus the built host-runtime sidecar instead of staying replay-only
- AIE binding validation now checks:
  - `codegen/aie/aie_codegen.json`
  - `codegen/aie/toolchain.json`
  - `codegen/aie/host.py`

Current scope:

- extension-owned planning + emission
- Python-space replay remains canonical
- reference toolchain execution + host-runtime launch exist for the emitted
  package contract
