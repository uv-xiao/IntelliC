# HTP TODO

`docs/todo/` tracks the part of HTP that is not finished yet.

This tree is organized as direct TODO feature documents. `README.md` gives the summary and completion statistics; the detailed remaining work lives in `docs/todo/` and the research-backed report under `docs/todo/reports/`.

## How to use this tree

For feature work:
1. choose one feature-sized gap from the summaries below
2. read the relevant detailed TODO file under `docs/todo/`
3. create a task file under `docs/in_progress/`
4. open a feature PR from `htp/feat-*`
5. move landed behavior into `docs/design/` before merge

## Completion statistics

### Overall

- total tracked TODO checklist items: 56
- complete: 40
- partial: 10
- open: 6
- completion ratio: about 71%

### By area

| Layer | Complete | Partial | Open | Total |
| --- | ---: | ---: | ---: | ---: |
| Compiler model, semantics, typing | 6 | 2 | 2 | 10 |
| Programming surfaces | 10 | 0 | 0 | 10 |
| Pipeline and solver | 6 | 2 | 1 | 9 |
| Artifacts, replay, debug | 5 | 2 | 1 | 8 |
| Backends and extensions | 8 | 2 | 1 | 11 |
| Agent product and workflow | 5 | 2 | 1 | 8 |

## Feature summaries

- `docs/todo/01_compiler_model.md`
  - remaining work: broaden semantic/type/layout/effect breadth beyond the newly landed fused-elementwise semantics and deepen routine semantics
- `docs/todo/02_programming_surfaces.md`
  - remaining work: no standalone open item; future surface work now rolls into richer semantics and backend depth
- `docs/todo/03_pipeline_and_solver.md`
  - remaining work: richer search/composition and broader MLIR island breadth
- `docs/todo/04_artifacts_replay_debug.md`
  - remaining work: broader consistency checks and deeper replay/reference coverage
- `docs/todo/05_backends_and_extensions.md`
  - remaining work: deepen PTO, NV-GPU, and AIE rather than changing the architecture; the remaining gap is backend depth, not the Arknife reuse boundary
- `docs/todo/06_agent_product_and_workflow.md`
  - remaining work: stronger autonomous loops and continued quality-discipline tightening

## Detailed remaining TODO files

- `docs/todo/01_compiler_model.md`
- `docs/todo/02_programming_surfaces.md`
- `docs/todo/03_pipeline_and_solver.md`
- `docs/todo/04_artifacts_replay_debug.md`
- `docs/todo/05_backends_and_extensions.md`
- `docs/todo/06_agent_product_and_workflow.md`
- `docs/todo/reports/retargetable_extensibility_report.md`
