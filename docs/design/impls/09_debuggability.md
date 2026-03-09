# Impl: Debuggability and Introspection

Current code anchors:

- diagnostic catalog: `htp/diagnostics.py`
- semantic diff and bisect tooling: `htp/tools.py`
- replay/runtime diagnostics: `htp/runtime/errors.py`
- binding logs and adapter traces: `htp/bindings/base.py`,
  `htp/bindings/pto_runtime_adapter.py`, `htp/bindings/nvgpu_cuda_adapter.py`
- pass trace emission: `htp/passes/trace.py`

Implemented behavior:

- diagnostics are stable-coded and machine-readable
- `htp explain <code>` resolves both exact-code and family explanations
- family coverage now includes:
  - `HTP.BINDINGS.*`
  - `HTP.REPLAY.*`
  - `HTP.TYPECHECK.*`
  - `HTP.LAYOUT.*`
  - `HTP.EFFECT.*`
  - `HTP.PROTOCOL.*`
  - `HTP.SOLVER.*`
- semantic diff now compares:
  - manifest target / outputs / extensions
  - staged semantic sidecars
  - ids / maps
  - current-stage replay stubs
  - `ir/pass_trace.jsonl`
  - node-aware blame for added/removed entities and bindings
- replay, build, and run paths emit stable refs to logs or adapter traces where
  available

Current debug guidance:

## Stage-local debugging

- Start with `ir/pass_trace.jsonl` to identify the first pass that changed the
  contract surface.
- Use `htp diff --semantic <left> <right>` to compare:
  - semantic sidecars,
  - ids/maps,
  - replay stubs,
  - pass trace,
  - node-aware blame for changed entities/bindings.
- If replay fails, inspect:
  - `logs/replay_<stage>_<mode>_*.log`
  - `ir/stages/<id>/replay/stubs.json` when present
  - the blamed stage directory under `ir/stages/<id>/`

## Extension-island debugging

- Start from the island directory recorded on the stage:
  - for MLIR CSE: `ir/stages/<id>/islands/mlir_cse/`
- Inspect, in order:
  - `eligibility.json`
  - `pipeline.txt`
  - `input.mlir`
  - `output.mlir`
  - `ledger.json`
  - `import_summary.json`
  - `entity_map.json` / `binding_map.json`
- Requested-but-ineligible extension usage now fails in the solver before pass
  execution; inspect `ir/solver_failure.json` for `failed_rules` and `reasons`.

## Backend-toolchain debugging

- PTO:
  - inspect `logs/adapter_pto_*.json`
  - inspect `codegen/pto/pto_codegen.json`
  - inspect `build/toolchain.json`
  - if execution materialized binaries, inspect `build/pto/...`
- NV-GPU:
  - inspect `logs/adapter_nvgpu_*.json`
  - inspect `codegen/nvgpu/nvgpu_codegen.json`
  - inspect `build/toolchain.json`
  - if device build ran, inspect `build/nvgpu/...`
- AIE:
  - inspect `codegen/aie/aie_codegen.json`
  - inspect `codegen/aie/toolchain.json`
  - inspect `codegen/aie/mapping.json`, `codegen/aie/fifos.json`, and
    `codegen/aie/aie.mlir`

Scope note:

- this documents the currently implemented debug substrate
- broader future debug contracts stay under `docs/future/feats/09_debuggability.md`
