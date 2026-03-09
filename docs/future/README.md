# HTP Future Design Notes

This folder holds design and research material that is not fully implemented in
the current branch.

`docs/future/` is intentionally flat at the top level. There is no
`docs/future/design/` nesting anymore: if a document is not implemented yet, it
belongs directly under `docs/future/` or one of its immediate subfolders.

These documents are roadmap and rationale material. They are **not** the
normative description of the current implementation.

## Current boundary

What is already implemented in `htp/` and documented under `docs/design/`:

- implementation story and current proof points
- implemented feature catalog
- staged semantic substrate (`kernel_ir`, `workload_ir`, `types`, `layout`,
  `effects`, `schedule`)
- capability solver preflight and `ir/solver_failure.json`
- package tooling:
  - `htp replay`
  - `htp verify`
  - `htp diff --semantic`
  - `htp explain`
  - `htp bisect`
  - `htp minimize`
- pass contracts and staged replay artifacts
- registered pass and pipeline surfaces
- WSP and CSP programming surfaces
- staged warp-specialization and software-pipeline passes
- one extension-owned MLIR CSE path under `htp_ext/mlir_cse/`
- expanded MLIR CSE eligibility for canonical scalar elementwise kernels
- MLIR island identity maps and registered pipeline participation
- one extension-owned AIE artifact path under `htp_ext/aie/`
- real PTO `a2a3sim` numerical execution for vector add
- real NV-GPU numerical execution for GEMM on the current example path

What remains in this folder is the broader design/research scope beyond that
implemented boundary.

## Priority order for the next phase

The remaining future scope is not flat. The current recommended order is:

1. **Solver + composition layer**
   - richer extension/package composition rules
2. **Agent-native productization**
   - built-in agent loop
   - minimize surface
   - richer provenance and policy contracts
3. **Broader semantic surface**
   - more kernel/workload/dataflow operations
   - stronger channel/process semantics than the current channel/FIFO baseline
4. **MLIR round-trip expansion**
   - move beyond the current scalar elementwise CSE subset
5. **Optional extension backends**
   - AIE toolchain execution beyond artifact emission
   - additional extension backends

## How to read this folder now

- `gap_checklist.md` — code-vs-future implementation checklist
- `analysis.md` — why the broader design still matters after the current
  implementation milestone
- `features.md` — the broader target feature surface beyond what is already in
  `docs/design/features.md`
- `impls/03_capability_solver.md` — remaining solver evolution beyond the current landing
- `impls/10_agentic_tooling.md` — autonomous loop design beyond the current tooling
- `reports/retargetable_extensibility_report.md` — research evidence for the
  architecture choice
