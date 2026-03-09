# HTP Design — Implemented Surface

`docs/design/` now tracks the design that is backed by code in this branch.
Unimplemented or research-only material lives under `docs/future/`.

## Read order

- `docs/design/code_map.md` — implementation entrypoints and file map
- `docs/design/implementations.md` — current architecture and contracts
- `docs/design/examples.md` — implemented example flows

## Implemented deep dives

- `docs/design/impls/01_ir_model.md` — AST-first staged IR and identity contracts
- `docs/design/impls/02_pass_manager.md` — pass execution and stage emission
- `docs/design/impls/03_capability_solver.md` — solver preflight and unsat reporting
- `docs/design/impls/04_artifact_manifest.md` — artifact and manifest schemas
- `docs/design/impls/05_backend_pto.md` — PTO package/build/run contract
- `docs/design/impls/06_backend_aie.md` — AIE extension backend artifact contract
- `docs/design/impls/07_binding_interface.md` — validate/build/load/run/replay lifecycle
- `docs/design/impls/08_testing.md` — verification expectations
- `docs/design/impls/10_agentic_tooling.md` — replay/verify/diff/explain tooling
- `docs/design/impls/11_warp_specialization_pipelining.md` — staged warp/pipeline pass sequence
- `docs/design/impls/12_mlir_roundtrip_island.md` — implemented MLIR round-trip extension path
- `docs/design/impls/13_backend_nvgpu.md` — NV-GPU package/build/run contract

## Runnable examples

- `examples/pto_pypto_vector_add/`
- `examples/nvgpu_arknife_gemm/`
- `docs/examples/`

## Future material

- `docs/future/README.md`
