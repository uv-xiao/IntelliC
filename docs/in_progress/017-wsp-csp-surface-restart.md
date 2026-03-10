# Restart WSP/CSP public surfaces and flagship examples

- ID: `017-wsp-csp-surface-restart`
- Branch: `htp/feat-wsp-csp-surface-restart`
- PR: `TBD`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Rework the public WSP/CSP authoring surfaces and their flagship examples so they read like real human-written programs rather than schedule metadata wrappers around shallow kernels. The new surface should learn directly from `references/pypto/`, `references/triton-distributed-knowingnothing/python/little_kernel/`, and `references/arknife/`, while still lowering through HTP's shared program model.

## Why

- contract gap: the current WSP/CSP examples are still semantically thin and mostly decorate a single kernel call with schedule metadata
- user-facing impact: flagship examples fail the human-first bar and do not convincingly show WSP/CSP as meaningful programming models
- architectural reason: HTP's extensibility claim depends on one shared compiler substrate, so richer WSP/CSP surfaces must integrate organically with the existing kernel/workload semantics instead of becoming sidecar DSLs

## Scope Checklist

- [ ] redesign the public WSP surface around clearer staged mainloop / role / schedule authoring
- [ ] redesign the public CSP surface around meaningful producer-consumer/channel protocol authoring
- [ ] rewrite the flagship WSP/CSP examples against the new surfaces using reference-backed semantics
- [ ] update design/todo docs and agent guidance for the refined surface quality bar
- [ ] verify example behavior, replay artifacts, and public-surface tests

## Code Surfaces

- producer: `htp/wsp/__init__.py`, `htp/csp/__init__.py`, `htp/kernel.py`, example code
- validator/binding: `htp/passes/program_model.py`, solver/tests if payload shape changes
- tests: `tests/test_public_surfaces.py`, `tests/examples/test_examples.py`, WSP/CSP pipeline tests
- docs: `docs/design/programming_surfaces.md`, `docs/todo/programming_surfaces.md`, example-local `README.md`, `AGENTS.md`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating bug or gap
- [ ] human-friendly example updated or added
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [ ] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. land WSP/CSP surface changes
3. rewrite flagship examples and tests
4. sync docs and guidance
5. rebase, review, and merge

## Review Notes

Reviewers should inspect whether the new examples actually model meaningful staged work and protocol structure, not just nicer syntax over the old shallow payloads.
