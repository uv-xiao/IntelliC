# HTP TODO

`docs/todo/` tracks feature work that is still open.

## Current state

There is currently one reopened broad-topic TODO document in this repository:
`docs/todo/programming_surfaces.md`.

The rest of the previously tracked broad-topic gaps remain implemented and
documented under `docs/design/`.

## Completion statistics

### Overall

- total tracked TODO checklist items: 60
- complete: 56
- partial: 1
- open: 3
- completion ratio: about 93%

### By topic

| Topic | Complete | Partial | Open | Total |
| --- | ---: | ---: | ---: | ---: |
| Compiler model, semantics, typing | 10 | 0 | 0 | 10 |
| Programming surfaces | 10 | 1 | 3 | 14 |
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

## Active TODO files

- `docs/todo/programming_surfaces.md`
