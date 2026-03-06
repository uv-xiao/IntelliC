# HTP Redo (docs-only) — Index

This folder is the **redo design** described by `docs/design/REDO.md`.

## Read order

- `docs/design/analysis.md` — positioning and methodology (WHY)
- `docs/design/features.md` — feature catalog (WHAT)
- `docs/design/implementations.md` — architecture and contracts (HOW)
- `docs/design/story.md` — cohesive end-to-end narrative (WHY→WHAT→HOW)
- `docs/design/examples.md` — end-to-end examples

## Completeness criteria

- `docs/design/acceptance_checklist.md`

## Deep dives

- Features: `docs/design/feats/`
- Implementation components: `docs/design/impls/`
- Retargetability evidence report: `docs/design/reports/retargetable_extensibility_report.md`

Notable deep dives:

- Warp specialization + pipelining case study: `docs/design/impls/11_case_study_warp_specialization_pipelining.md`
- MLIR round-trip island contract: `docs/design/impls/12_mlir_roundtrip_island.md`

## Scope note

This redo is **docs-only**: it does not rename packages, move code, or change build scripts yet.
