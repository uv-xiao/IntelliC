# HTP TODO

`docs/todo/` tracks feature work that is still open.

## Current state

There are currently no open TODO feature documents in this repository.

The previously tracked broad-topic gaps are now implemented and documented under `docs/design/`.
New future work should re-enter this tree only when it is specific enough to justify a new feature-sized task and PR.

## Completion statistics

### Overall

- total tracked TODO checklist items: 56
- complete: 56
- partial: 0
- open: 0
- completion ratio: 100%

### By topic

| Topic | Complete | Partial | Open | Total |
| --- | ---: | ---: | ---: | ---: |
| Compiler model, semantics, typing | 10 | 0 | 0 | 10 |
| Programming surfaces | 10 | 0 | 0 | 10 |
| Pipeline and solver | 9 | 0 | 0 | 9 |
| Artifacts, replay, debug | 8 | 0 | 0 | 8 |
| Backends and extensions | 11 | 0 | 0 | 11 |
| Agent product and workflow | 8 | 0 | 0 | 8 |

## How to use this tree when new work appears

1. add the new gap to this README
2. if the work is broad enough, add a matching detailed TODO file under `docs/todo/`
3. create a task file under `docs/in_progress/`
4. implement the feature on `htp/feat-<topic>`
5. move the landed behavior into `docs/design/` and clear the TODO entry before merge

## Supporting analysis

- `docs/research/retargetable_extensibility_report.md`
