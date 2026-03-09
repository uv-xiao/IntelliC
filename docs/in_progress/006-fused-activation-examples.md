# Fused Activation Examples and Richer Elementwise Semantics

- ID: `006-fused-activation-examples`
- Branch: `htp/feat-fused-activation-examples`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Broaden the semantic and backend surface enough to support harder, pypto-calibrated fused elementwise examples, then add those examples as human-friendly public proof cases.

## Why

- `docs/todo/layers/01_compiler_model.md` still calls out semantic breadth as incomplete
- `docs/todo/layers/02_programming_surfaces.md` still leaves flagship difficulty as partial
- the current public examples are more human-friendly after `005`, but they are still too small compared with `references/pypto/examples/language/intermediate/`

## Scope Checklist

- [ ] add richer unary/elementwise semantic ops needed for fused activation examples
- [ ] broaden NV-GPU and PTO lowering/emission for the supported fused-elementwise subset
- [ ] add at least one harder pypto-calibrated public example
- [ ] add focused contract and numerical tests
- [ ] update `docs/design/` and `docs/todo/`
- [ ] remove this file from `docs/in_progress/` before merge

## Code Surfaces

- semantic model: `htp/ir/op_specs.py`, `htp/passes/program_model.py`
- public surface: `htp/kernel.py`, examples under `examples/`
- backends: `htp/backends/nvgpu/`, `htp/backends/pto/`
- docs/tests: `docs/design/`, `docs/todo/`, `tests/`

## Test and Verification Plan

- [ ] one happy-path compile/replay test for the new fused example
- [ ] one malformed/unsupported-case test for the broadened lowering contract
- [ ] one numerical backend-path regression where feasible
- [ ] `pytest -q`
- [ ] `pre-commit run --all-files`
