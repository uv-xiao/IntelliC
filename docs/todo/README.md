# HTP TODO

`docs/todo/` tracks the part of HTP that is not finished yet.

This tree is also organized by layers. `README.md` is the summary checklist; the detailed remaining design lives in `docs/todo/layers/` plus the research report under `docs/todo/reports/`.

## Remaining work summary

Status markers:
- `[x]` landed in `docs/design/`
- `[~]` partial; implemented substrate exists but the full feature surface does not
- `[ ]` not implemented yet

### Layer summary

- `[~]` Layer 1 — compiler model breadth: the shared semantic/type/layout/effect core exists, but it is still narrower than the final target
- `[~]` Layer 2 — programming surfaces: kernel, WSP, CSP, and simple workload routines exist, but richer Python-native user surfaces are still missing
- `[~]` Layer 3 — pipeline and solver: registry-driven composition exists, but deeper search, richer provider composition, and broader MLIR islands remain
- `[~]` Layer 4 — artifacts, replay, and debug: the contract surface is strong, but broader consistency checks and debug experiences remain
- `[~]` Layer 5 — backends and extensions: PTO, NV-GPU, and AIE are real, but backend breadth and depth still remain
- `[~]` Layer 6 — agent product and workflow: the repo workflow is now disciplined, but broader autonomous-development features are still future work

## Detailed remaining layers

- `docs/todo/layers/01_compiler_model.md`
- `docs/todo/layers/02_programming_surfaces.md`
- `docs/todo/layers/03_pipeline_and_solver.md`
- `docs/todo/layers/04_artifacts_replay_debug.md`
- `docs/todo/layers/05_backends_and_extensions.md`
- `docs/todo/layers/06_agent_product_and_workflow.md`
- `docs/todo/reports/retargetable_extensibility_report.md`
