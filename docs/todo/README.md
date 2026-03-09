# HTP TODO Surface

`docs/todo/` tracks the unimplemented part of HTP.

This directory is the planning surface for new feature branches:
- start from the checklist below,
- choose one feature-sized gap,
- create a task file under `docs/in_progress/`,
- open a PR from `htp/feat-*`,
- and move landed behavior into `docs/design/` before merge.

Status markers:
- `[x]` landed in code and documented in `docs/design/`
- `[~]` partially landed; more work remains
- `[ ]` not implemented yet

## Summary checklist

### Solver and composition
- `[x]` registered pipeline and pass providers are solver-visible
- `[ ]` continue broadening solver composition only when it unblocks deeper backend/runtime work

### Agent development product
- `[~]` agent tooling and repo workflow discipline are real, but broader autonomous-development controls remain

### Semantics and typing
- `[~]` shared semantic payloads, layout, effects, schedule, WSP, and CSP are real
- `[ ]` broader semantic breadth remains for advanced kernels and richer backend discharge

### MLIR and extension composition
- `[~]` the MLIR round-trip extension is real but still narrow

### Backends
- `[~]` PTO is real for `a2a3sim`, but broader orchestration and device coverage remain
- `[~]` NV-GPU is real for CUDA execution, but broader lowering, adapter breadth, profiling, and Blackwell specialization remain
- `[x]` AIE now has planning, emission, reference toolchain build outputs, and host-runtime launch
- `[ ]` a next extension backend is still optional future work

### Validation, debug, and documentation hygiene
- `[~]` manifest/debug contracts are substantially implemented, but some binding/extension consistency and docs migration work remain
- `[~]` docs migration from TODO to design must continue as features land

## Detailed TODO files

### Narrative and rationale
- `docs/todo/story.md`
- `docs/todo/analysis.md`
- `docs/todo/features.md`
- `docs/todo/reports/retargetable_extensibility_report.md`

### Layered feature details
- `docs/todo/feats/`
- `docs/todo/impls/`

### Operational checklist
- `docs/todo/gap_checklist.md`
- `docs/todo/acceptance_checklist.md`
- `docs/todo/REDO.md`
