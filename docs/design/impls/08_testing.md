# Impl: Testing Strategy (for compiler-as-artifact)

## Goals

- ensure stable artifact contracts
- ensure diagnostics are actionable and stable
- ensure stage replay (`RunnablePy`) is preserved where promised

## Recommended test classes

### 1) Golden artifact tests

Compile known examples and assert:

- `manifest.json` schema + required fields exist,
- `ir/pass_trace.jsonl` exists and is parseable,
- stage directories exist with required dumps,
- backend contract outputs exist under `codegen/<backend>/...`.

Golden artifacts should compare:

- stable JSON files (manifest, toolchain pins, mapping/fifos sidecars),
- and “exists + size + hash” for large textual outputs (MLIR, C++) where exact diff is noisy.

### 2) Diagnostic stability tests

For known-bad programs, assert:

- stable diagnostic `code` values,
- stable blame shape (`node_id` present),
- and stable structured payload schema.

Avoid asserting full human-readable messages; those can change.

### 3) Contract validation tests

Validate package directory against declared contracts:

- backend artifact contract validators (e.g. PTO requires `kernel_config.py`; AIE requires `aie.mlir` + sidecars),
- pipeline contract validators (final capabilities satisfied),
- replay validators (if a pass claims `RunnablePy(preserves)`, then `program.py` exists and imports succeed in `sim` mode).

### 4) Replay equivalence tests (when simulators exist)

When `mode="sim"` is supported:

- run stage `sN` and `sN+1` via replay and compare observable outputs,
- use this to localize semantic regressions introduced by passes.

This is the backbone for long-term “healthy” development and for automated agent loops.
