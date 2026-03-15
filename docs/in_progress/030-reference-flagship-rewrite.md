# In-Progress — Reference Flagship Rewrite

- PR: `#pending`
- Branch: `htp/feat-reference-flagship-rewrite`
- Status: in progress

## Goal

Close the last programming-surface TODO by rewriting the flagship WSP/CSP examples so they better reflect the semantic richness of the PyPTO, LittleKernel, and Arknife references.

## Scope

- deepen the flagship WSP examples with richer staged task structure and schedule metadata
- deepen the flagship CSP example with a more realistic multi-channel, multi-process pipeline
- update example-local docs and regression tests
- close the remaining programming-surfaces TODO and clean stale in-progress task state

## Test plan

- extend example tests to cover the richer WSP/CSP flows
- run `pytest -q`
- run `pre-commit run --all-files`

## Exit criteria

- the remaining open checklist item in `docs/todo/programming_surfaces.md` is closed
- `docs/todo/README.md` reports no remaining TODO checklist items
- stale `docs/in_progress/029-csp-authored-bodies.md` is removed
- this task file is removed before merge
