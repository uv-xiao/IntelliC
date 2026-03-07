# HTP Design — Index

This folder is the **redo design** described by `docs/design/REDO.md`.

## Read order

- `docs/design/analysis.md` — positioning and methodology (WHY)
- `docs/design/features.md` — feature catalog (WHAT)
- `docs/design/implementations.md` — architecture and contracts (HOW)
- `docs/design/story.md` — cohesive end-to-end narrative (WHY→WHAT→HOW)
- `docs/design/examples.md` — end-to-end examples
- `docs/design/code_map.md` — where the current implementation lives

## Completeness criteria

- `docs/design/acceptance_checklist.md`

## Deep dives

- Features: `docs/design/feats/`
- Implementation components: `docs/design/impls/`
- Retargetability evidence report: `docs/design/reports/retargetable_extensibility_report.md`

Notable deep dives:

- Warp specialization + pipelining case study: `docs/design/impls/11_case_study_warp_specialization_pipelining.md`
- MLIR round-trip island contract: `docs/design/impls/12_mlir_roundtrip_island.md`
- NV-GPU backend contract: `docs/design/impls/13_backend_nvgpu.md`

## Runnable examples

- `examples/pto_pypto_vector_add/` — PyPTO-inspired PTO example
- `examples/nvgpu_arknife_gemm/` — Arknife-inspired NV-GPU example
- `docs/examples/` — standalone walkthroughs for those runnable examples
