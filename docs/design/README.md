# HTP Design

`docs/design/` is the normative description of what is implemented in this repository.

This tree is intentionally organized by layers. Each layer file combines:
- the implemented contract,
- the main code anchors,
- and a small visual model so readers can orient themselves quickly.

## Architecture map

```text
Python Authoring
    |
    v
Compiler Model + Typing
    |
    v
Passes + Solver
    |
    v
Artifacts + Replay + Debug
    |
    v
Backends + Extensions
    |
    v
Agent Product + Workflow
```

## Read order

- `docs/story.md` — final intended framework story
- `docs/design/README.md` — implemented architecture index
- `docs/design/layers/01_compiler_model.md`
- `docs/design/layers/02_programming_surfaces.md`
- `docs/design/layers/03_pipeline_and_solver.md`
- `docs/design/layers/04_artifacts_replay_debug.md`
- `docs/design/layers/05_backends_and_extensions.md`
- `docs/design/layers/06_agent_product_and_workflow.md`
- `docs/design/examples/README.md`

## Implemented layers

- `docs/design/layers/01_compiler_model.md` — canonical Python-space compiler model, semantics, typing, layout, effects
- `docs/design/layers/02_programming_surfaces.md` — kernel, WSP, CSP, and workload authoring surfaces
- `docs/design/layers/03_pipeline_and_solver.md` — pass spine, capability solver, staged transformations, MLIR round-trip participation
- `docs/design/layers/04_artifacts_replay_debug.md` — manifest, staged artifacts, replay, diagnostics, and verification surface
- `docs/design/layers/05_backends_and_extensions.md` — PTO, NV-GPU, AIE, and extension integration
- `docs/design/layers/06_agent_product_and_workflow.md` — agent-facing tooling and repository workflow

## Examples

Runnable example walkthroughs live in `docs/design/examples/` and are backed by code under `examples/`.

## Out of scope for this tree

- unimplemented or partial future work → `docs/todo/`
- active feature tasks → `docs/in_progress/`
- references and research corpora → `docs/reference/`, `docs/research/`
