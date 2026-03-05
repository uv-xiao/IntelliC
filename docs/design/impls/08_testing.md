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
- stage directories include `analysis/index.json` when passes claim analysis outputs,
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

---

## Additional “long-term health” gates (recommended)

These are cheap checks that prevent slow accumulation of implicit invariants:

### 5) Analysis freshness tests

- if a transform pass invalidates an analysis capability, ensure downstream passes do not consume stale files
- if an analysis is required, ensure it is explicitly listed in `analysis_requires` in the consumer pass contract

### 6) Determinism tests (when promised)

- for passes marked `deterministic=true`, run twice and assert identical:
  - `program.pyast.json` (structural dump)
  - analysis outputs (byte-for-byte or semantic hash)
  - manifest stage digests (when available)
