# HTP TODO

`docs/todo/` tracks the part of HTP that is not finished yet.

This tree is organized by layers. `README.md` gives the summary and completion statistics; the detailed remaining work lives in `docs/todo/layers/` and the research-backed report under `docs/todo/reports/`.

## How to use this tree

For feature work:
1. choose one feature-sized gap from the layer summaries below
2. read the relevant detailed layer file under `docs/todo/layers/`
3. create a task file under `docs/in_progress/`
4. open a feature PR from `htp/feat-*`
5. move landed behavior into `docs/design/` before merge

## Completion statistics

### Overall

- total tracked TODO checklist items: 54
- complete: 36
- partial: 11
- open: 7
- completion ratio: about 67%

### By layer

| Layer | Complete | Partial | Open | Total |
| --- | ---: | ---: | ---: | ---: |
| Compiler model, semantics, typing | 6 | 2 | 2 | 10 |
| Programming surfaces | 8 | 0 | 1 | 9 |
| Pipeline and solver | 6 | 2 | 1 | 9 |
| Artifacts, replay, debug | 5 | 2 | 1 | 8 |
| Backends and extensions | 6 | 3 | 1 | 10 |
| Agent product and workflow | 5 | 2 | 1 | 8 |

## Layer summaries

- `docs/todo/layers/01_compiler_model.md`
  - remaining work: broaden semantic/type/layout/effect breadth beyond the newly landed fused-elementwise semantics and deepen routine semantics
- `docs/todo/layers/02_programming_surfaces.md`
  - remaining work: finish the written AST-centric comparison against LittleKernel and use it to drive the next surface pass; the current example tree is now grouped under `examples/pto`, `examples/nvgpu`, `examples/patterns`, `examples/extensions`, and `examples/workloads`
- `docs/todo/layers/03_pipeline_and_solver.md`
  - remaining work: richer search/composition and broader MLIR island breadth
- `docs/todo/layers/04_artifacts_replay_debug.md`
  - remaining work: broader consistency checks and deeper replay/reference coverage
- `docs/todo/layers/05_backends_and_extensions.md`
  - remaining work: deepen PTO, NV-GPU, and AIE rather than changing the architecture
- `docs/todo/layers/06_agent_product_and_workflow.md`
  - remaining work: stronger autonomous loops and continued quality-discipline tightening

## Detailed remaining layers

- `docs/todo/layers/01_compiler_model.md`
- `docs/todo/layers/02_programming_surfaces.md`
- `docs/todo/layers/03_pipeline_and_solver.md`
- `docs/todo/layers/04_artifacts_replay_debug.md`
- `docs/todo/layers/05_backends_and_extensions.md`
- `docs/todo/layers/06_agent_product_and_workflow.md`
- `docs/todo/reports/retargetable_extensibility_report.md`
- `docs/todo/reports/littlekernel_ast_comparison.md`
