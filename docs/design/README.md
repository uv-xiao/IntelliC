# HTP Design

`docs/design/` is the normative description of what is implemented in this repository.

This tree is intentionally organized as broad implemented-topic documents. Each file combines:
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
- `docs/design/compiler_model.md`
- `docs/design/programming_surfaces.md`
- `docs/design/pipeline_and_solver.md`
- `docs/design/artifacts_replay_debug.md`
- `docs/design/backends_and_extensions.md`
- `docs/design/agent_product_and_workflow.md`
- `docs/design/littlekernel_ast_comparison.md`
- `docs/design/status_and_alignment.md`

## Implemented feature documents

- `docs/design/compiler_model.md` — canonical Python-space compiler model, semantics, typing, layout, effects
- `docs/design/programming_surfaces.md` — kernel, WSP, CSP, and workload authoring surfaces
- `docs/design/pipeline_and_solver.md` — pass spine, capability solver, staged transformations, MLIR round-trip participation
- `docs/design/artifacts_replay_debug.md` — manifest, staged artifacts, replay, diagnostics, and verification surface
- `docs/design/backends_and_extensions.md` — PTO, NV-GPU, AIE, extension integration, and Arknife-style NV-GPU support
- `docs/design/agent_product_and_workflow.md` — agent-facing tooling and repository workflow
- `docs/design/littlekernel_ast_comparison.md` — completed LittleKernel comparison and the surface rules extracted from it
- `docs/design/status_and_alignment.md` — current repository review: what is solid, what is narrow, and what has been reopened as TODO

## Examples

Runnable example walkthroughs live with the examples themselves under
`examples/**/README.md`. This is intentional: public example documentation stays
co-located with the code it explains.

## Out of scope for this tree

- active feature tasks → `docs/in_progress/`
- future work staging area → `docs/todo/README.md`
- references and research corpora → `docs/reference/`, `docs/research/`
