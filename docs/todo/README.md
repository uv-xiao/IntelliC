# HTP TODO

`docs/todo/` tracks feature work that is still open.

## Current state

The review reopened one broad-topic TODO document:

- `docs/todo/alignment_and_product_gaps.md`

That topic now tracks the remaining product gaps after the AST-all-the-way
stage-contract slice landed: programming-surface quality, flagship example
realism, backend depth, and documentation discipline.

## Completion statistics

### Overall

- total tracked TODO checklist items: 81
- complete: 72
- partial: 0
- open: 9
- completion ratio: 88.9%

### By topic

| Topic | Complete | Partial | Open | Total |
| --- | ---: | ---: | ---: | ---: |
| Compiler model, semantics, typing | 13 | 0 | 0 | 13 |
| Programming surfaces and examples | 19 | 0 | 8 | 27 |
| Pipeline and solver | 10 | 0 | 0 | 10 |
| Artifacts, replay, debug | 8 | 0 | 0 | 8 |
| Backends and extensions | 11 | 0 | 3 | 14 |
| Agent product and workflow | 8 | 0 | 1 | 9 |

## How to use this tree when new work appears

1. add the new gap to this README
2. if the work is broad enough, add a matching detailed TODO file under `docs/todo/`
3. create a task file under `docs/in_progress/`
4. implement the feature on `htp/feat-<topic>`
5. move the landed behavior into `docs/design/` and clear the TODO entry before merge

## Supporting analysis

- `docs/research/retargetable_extensibility_report.md`

## Active TODO files

- `docs/todo/alignment_and_product_gaps.md`
