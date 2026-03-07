# HTP Future Design Notes

This folder holds design and research material that is not fully implemented in
the current branch.

Moved here from `docs/design/`:

- broader methodology and story docs
- feature catalogs that exceed the current code
- capability-solver and agent-tooling proposals
- MLIR round-trip island and AIE backend plans
- warp-specialization / pipelining case studies
- retargetability research reports

These documents remain useful as roadmap and rationale, but they are not the
normative description of the current implementation.

## Current boundary

What is already implemented in `htp/` and documented under `docs/design/`:

- staged semantic substrate (`kernel_ir`, `workload_ir`, `types`, `layout`,
  `effects`, `schedule`)
- pass contracts and staged replay artifacts
- one extension-owned MLIR CSE path under `htp_ext/mlir_cse/`
- real PTO `a2a3sim` numerical execution for vector add
- real NV-GPU numerical execution for GEMM on the current example path

What remains in this folder is the broader design/research scope beyond that
implemented boundary.

## Priority order for the next phase

The remaining future scope is not flat. The current recommended order is:

1. **Solver + composition layer**
   - capability solver
   - richer extension/package composition rules
2. **Agent-native productization**
   - built-in agent loop
   - semantic diff / minimize / verify surfaces
   - provenance and policy contracts
3. **Broader semantic surface**
   - richer kernel/workload/dataflow operations
   - stronger channel/process semantics
4. **MLIR round-trip expansion**
   - move beyond the current CSE-only extension path
5. **Optional extension backends**
   - AIE / MLIR-AIE artifact emission and toolchain contracts

## How to read this folder now

- `analysis.md` — why the broader design still matters after the current
  implementation milestone
- `features.md` — the complete target feature surface
- `impls/03_capability_solver.md` — next major architecture gap
- `impls/10_agentic_tooling.md` — concrete agent loop design
- `reports/retargetable_extensibility_report.md` — research evidence for the
  architecture choice
