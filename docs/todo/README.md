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
- complete: 50
- partial: 3
- open: 2
- completion ratio: about 89%

### By topic

| Topic | Complete | Partial | Open | Total |
| --- | ---: | ---: | ---: | ---: |
| Compiler model, semantics, typing | 10 | 0 | 0 | 10 |
| Programming surfaces | 10 | 0 | 0 | 10 |
| Pipeline and solver | 9 | 0 | 0 | 9 |
| Artifacts, replay, debug | 8 | 0 | 0 | 8 |
| Backends and extensions | 8 | 2 | 1 | 11 |
| Agent product and workflow | 5 | 2 | 1 | 8 |

## Feature summaries

- `docs/todo/compiler_model.md`
  - remaining work: no standalone open item; future semantic work now rolls into backend depth and agent workflow rather than a missing compiler-model substrate
- `docs/todo/programming_surfaces.md`
  - remaining work: no standalone open item; the latest pass landed richer WSP task roles/stage plans and CSP process roles/compute steps, so future surface work now rolls into richer semantics and backend depth
- `docs/todo/pipeline_and_solver.md`
  - remaining work: no standalone open item; future work now rolls into semantics, backends, and agent workflow rather than a separate solver-architecture gap
- `docs/todo/artifacts_replay_debug.md`
  - remaining work: no standalone open item; future replay work now rolls into compiler-model and backend-depth topics rather than a separate package/debug gap
- `docs/todo/backends_and_extensions.md`
  - remaining work: deepen PTO, NV-GPU, and AIE rather than changing the architecture; the remaining gap is backend depth, not the Arknife reuse boundary
- `docs/todo/agent_product_and_workflow.md`
  - remaining work: stronger autonomous loops and continued quality-discipline tightening

## Detailed remaining TODO files

- `docs/todo/compiler_model.md`
- `docs/todo/programming_surfaces.md`
- `docs/todo/pipeline_and_solver.md`
- `docs/todo/artifacts_replay_debug.md`
- `docs/todo/backends_and_extensions.md`
- `docs/todo/agent_product_and_workflow.md`
- `docs/todo/reports/retargetable_extensibility_report.md`
