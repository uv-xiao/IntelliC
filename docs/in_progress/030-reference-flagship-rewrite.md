# In-Progress — Reference Flagship Rewrite

- PR: `#65`
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

- the remaining open programming-surfaces checklist item is closed
- `docs/todo/README.md` reports no remaining TODO checklist items
- stale `docs/in_progress/029-csp-authored-bodies.md` is removed
- this task file is removed before merge

## Progress

- deepened the flagship WSP examples into four-task staged pipelines
- deepened the flagship CSP example into a four-process, three-channel pipeline
- updated example-local docs and design docs to describe the richer narratives
- removed the last open programming-surfaces TODO from `docs/todo/`
- removed the stale completed CSP task file

## Verification

- `pytest -q`
- `pre-commit run --all-files`
