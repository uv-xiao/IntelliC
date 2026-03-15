# In-Progress — WSP Authored Bodies

- PR: `#63`
- Branch: `htp/feat-wsp-authored-bodies`
- Status: in progress

## Goal

Close the remaining WSP ergonomics gaps by making flagship workloads read like authored programs instead of schedule-builder chains.

## Scope

- add scoped/default schedule contexts for repeated WSP task settings
- replace string-only WSP stage markers with structured authored bodies
- remove string-tuple argument wiring in flagship WSP examples
- rewrite flagship WSP examples onto the new surface
- update design/todo docs to reflect the landed surface

## Test plan

- add public-surface tests for schedule defaults, bound kernel args, and stage-body capture
- update example tests for the rewritten WSP examples
- run `pytest -q`
- run `pre-commit run --all-files`

## Exit criteria

- WSP examples no longer repeat identical schedule boilerplate per task
- WSP examples no longer pass kernel arguments as raw string tuples
- WSP stage plans are emitted from structured authored bodies, not string lists
- docs/design and docs/todo are synchronized before merge

## Progress

- added `w.defaults(...)` for scoped schedule defaults
- added `w.args.<name>` bound kernel arguments for authored workloads
- added structured stage bodies through `task.prologue().step(...)` / `steady()` / `epilogue()`
- rewrote the WSP flagship examples onto the new surface
- updated design and TODO docs

## Verification

- `pre-commit run --all-files`
- `pytest -q`
