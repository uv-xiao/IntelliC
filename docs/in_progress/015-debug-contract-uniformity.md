# Debug contract uniformity across backends and extensions

- ID: `015-debug-contract-uniformity`
- Branch: `htp/feat-debug-contract-uniformity`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Broaden package validation and debug evidence so PTO, NV-GPU, AIE, and extension-owned sidecars feel uniformly inspectable. The outcome should close the open contract/debug-uniformity gap in `docs/todo/04_artifacts_replay_debug.md` and materially narrow the remaining partial validation-breadth item.

## Why

- contract gap: validation and diagnostics still vary too much between backend paths
- user-facing impact: some backend failures point precisely at artifacts and traces, while others still require manual digging
- architectural reason: artifact-first debugging only works if every backend and extension path exposes comparable evidence

## Scope Checklist

- [ ] identify the current validation / debug inconsistencies across PTO, NV-GPU, AIE, and extension sidecars
- [ ] add stronger uniform artifact references and schema checks for backend/extension sidecars
- [ ] make backend-specific diagnostics point to the same style of artifact / trace evidence
- [ ] add targeted regression tests for the new uniformity rules
- [ ] update `docs/design/04_artifacts_replay_debug.md`, `docs/todo/04_artifacts_replay_debug.md`, and `docs/todo/README.md`

## Code Surfaces

- `htp/bindings/validate.py`
- `htp/bindings/pto.py`
- `htp/bindings/nvgpu.py`
- `htp/bindings/aie.py`
- `htp/diagnostics.py`
- tests under `tests/bindings/`, `tests/golden/`, and `tests/tools/`

## Test and Verification Plan

Required:
- [ ] one happy-path validation test still passes
- [ ] one malformed-sidecar regression test per affected backend family
- [ ] `pytest -q`
- [ ] `pre-commit run --all-files`

Do not weaken validation or CI to make this pass. The point of this task is to make failures more informative and more uniform.

## Documentation Plan

- [ ] update `docs/design/` for landed behavior
- [ ] update `docs/todo/` to narrow or close the gap
- [ ] remove this file from `docs/in_progress/` before merge
