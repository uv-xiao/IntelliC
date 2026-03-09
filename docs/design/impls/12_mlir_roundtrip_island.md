# Impl: MLIR Round-Trip Island

Current code anchors:

- extension surface: `htp_ext/mlir_cse/island.py`
- MLIR export: `htp_ext/mlir_cse/export.py`
- MLIR import: `htp_ext/mlir_cse/import_.py`
- pass/file emission: `htp/passes/manager.py`
- solver template registration: `htp/pipeline/registry.py`, `htp/solver.py`
- tests: `tests/extensions/test_mlir_cse.py`,
  `tests/extensions/test_mlir_cse_pipeline.py`

Implemented behavior:

- `htp_ext.mlir_cse` is a registered pipeline participant, not only a
  standalone package emitter
- the extension contributes two real pass contracts:
  - `htp_ext.mlir_cse::export@1`
  - `htp_ext.mlir_cse::import@1`
- the solver can select the registered
  `htp.default+htp_ext.mlir_cse.v1` template when the extension is requested
  and the program is eligible
- pipeline execution resolves selected pass ids through the registered pass
  surface, so extension passes run through the same pass manager and pass trace
  as core passes

Implemented island artifacts:

- export stage:
  - `input.mlir`
  - `pipeline.txt`
  - `eligibility.json`
  - `ledger.json`
- import stage:
  - `output.mlir`
  - `import_summary.json`

Implemented import/export model:

- export lowers the eligible scalar elementwise subset into a textual MLIR
  module
- the island runs a deterministic built-in CSE pipeline over that MLIR module
- import parses the transformed `output.mlir` and reconstructs the reduced
  expression program from MLIR SSA plus the export ledger
- malformed MLIR import fails explicitly instead of silently falling back to
  Python-side rewrites

Current scope:

- eligible subset is still intentionally narrow: scalar `i32` elementwise
  add/mul kernels only
- identity maps (`entity_map.json`, `binding_map.json`) are not emitted yet for
  the MLIR extension
- the pass pipeline is recorded textually (`pipeline.txt`); there is no
  external `mlir-opt` integration yet

Broader MLIR coverage remains future work and stays under `docs/future/`.
