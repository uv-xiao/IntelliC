# In-Progress — CSP Authored Bodies

- PR: `#pending`
- Branch: `htp/feat-csp-authored-bodies`
- Status: in progress

## Goal

Close the remaining CSP frontend gap by replacing metadata-style process steps and string-wired arguments with authored process bodies over native HTP values.

## Scope

- add authored CSP process bodies built around `get(...)`, `put(...)`, and structured compute steps
- reduce or remove string-tuple argument wiring in flagship CSP examples
- rewrite the flagship CSP example onto the new surface
- update design and TODO docs

## Test plan

- add public-surface tests for authored CSP process bodies and bound argument capture
- update example tests for the rewritten CSP example
- run `pytest -q`
- run `pre-commit run --all-files`

## Exit criteria

- flagship CSP examples no longer rely on `.compute(\"name\", ...)` as the primary authored form
- flagship CSP examples no longer wire kernel arguments as raw string tuples
- docs/design and docs/todo are synchronized before merge
