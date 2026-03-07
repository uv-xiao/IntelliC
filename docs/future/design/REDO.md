# HTP Redo Plan (Docs-Only Orphan Branch)

This branch is intentionally **docs-only**. It exists to restart (“redo”) the design from first principles, with a focus on
**retargetable extensibility** across heterogeneous hardware (GPU/NPU/AIE/etc.).

The active redo design lives under:
- `docs/design/`

Historical PTO‑WSP v9/v10 design documents are preserved for reference only:
- `docs/reference/pto-wsp/`

Large external checkouts (Triton, papers, experimental repos) are local-only and **gitignored**:
- `references/`

## Goals (what this redo must accomplish)

1) **Retargetability by construction**
   - New hardware backends should be addable without forking “the whole compiler”.
   - Cross-target features (async pipelines, barriers, collectives, layouts) must have **explicit contracts** at stable
     layers, not be “re-discovered” from late-stage lowered IR.

2) **Real extensibility (composable extensions)**
   - Third parties can add dialects/ops, analyses, pipelines, and backends with well-defined surface areas.
   - Extension composition must be checkable (capabilities/effects/layout), not pass-order “tribal knowledge”.

3) **Semantics-honest artifacts**
   - Compilation outputs a stable “package”/artifact contract that runtimes can consume and tools can inspect.

## Non-goals (for this branch)

- No code refactor/rename/migration work in PTO‑WSP on this branch.
- No “keep old code around” snapshots in git history; only reference docs are preserved.
- `references/` is not committed (it is for local clones only).

## Deliverables (what should exist in git)

### Redo design docs (primary)
- `docs/design/analysis.md` — positioning + methodology (“why”)
- `docs/design/features.md` — feature catalog (“what”)
- `docs/design/implementations.md` — architecture/contracts (“how”)
- `docs/design/feats/*` — deep dives per feature area
- `docs/design/impls/*` — deep dives per implementation component

### Research reports (evidence)
- `docs/design/reports/retargetable_extensibility_report.md` — Triton/JAX/TileLang/MLIR comparative report

### Reference notes (context only)
- `docs/reference/*` — curated notes about related systems and hardware
- `docs/reference/pto-wsp/*` — PTO‑WSP v9/v10 historical docs

## Workstreams (what we design, in what order)

1) **Retargetability checklist + evaluation framework**
2) **IR model and semantic contracts**
3) **Capabilities + effects (checkability)**
4) **Pipelines + artifact contract**
5) **Backend interfaces**

## Definition of done (for the redo docs)

The redo is “done enough to implement” when:
- Every “must-have” semantic contract is explicit and testable in the spec.
- The extension points are enumerated with concrete interfaces and composition rules.
- At least 2–3 cross-target case studies (e.g., async pipeline + barriers, matmul accel, communication/scheduling) are
  analyzed end-to-end in `docs/design/reports/`.
