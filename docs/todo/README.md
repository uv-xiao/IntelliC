# HTP TODO

`docs/todo/` tracks feature work that is still open.

## Current state

The review reopened one broad-topic TODO document:

- `docs/todo/alignment_and_product_gaps.md`

That topic now tracks the remaining product gaps after the AST-all-the-way
stage-contract slice landed. The current PR closes the programming-surface,
flagship-example, and staged-artifact readability gaps; the remaining open
items are backend depth and broader repository documentation alignment.

## Completion statistics

### Overall

- total tracked TODO checklist items: 19
- complete: 14
- partial: 0
- open: 5
- completion ratio: 73.7%

### By topic

| Topic | Complete | Partial | Open | Total |
| --- | ---: | ---: | ---: | ---: |
| AST-all-the-way redesign | 6 | 0 | 0 | 6 |
| Programming surfaces | 4 | 0 | 0 | 4 |
| Examples | 3 | 0 | 0 | 3 |
| Backend depth | 0 | 0 | 3 | 3 |
| Pipeline and solver | 1 | 0 | 0 | 1 |
| Documentation alignment | 0 | 0 | 2 | 2 |

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
