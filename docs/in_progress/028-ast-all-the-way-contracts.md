# AST-All-the-Way Contracts

- ID: `028-ast-all-the-way-contracts`
- Branch: `htp/feat-ast-all-the-way-contracts`
- PR: `#67`
- Status: `implementing`
- Status: `verified-local`
- Owner: `Codex`

## Goal

Turn the newly stated project objective into real compiler contracts. This
feature is now a joint redesign of programming surfaces and the IR/artifact
system: it should formalize what it means for HTP to be human-friendly and
LLM-friendly through AST all the way, then thread that rule through the
compiler model, programming surfaces, pass contracts, artifact surfaces, and
extension boundaries.

## Why

- contract gap: the repo now states AST all the way as the primary project rule, but the implementation contracts do not yet enforce or expose that requirement consistently across programming surfaces, IR representation, passes, and extension boundaries
- user-facing impact: without a clear contract, stage artifacts may remain replayable while still drifting away from native Python readability and editability
- architectural reason: this is the first gap reopened by the design review and it should drive a joint redesign rather than a narrow replay-only adjustment

## Scope Checklist

- [x] write the redesign collection under `docs/in_progress/design/`
- [x] define the normative AST-all-the-way contract at global stage boundaries
- [x] define the flattened IR protocol around Python-AST carriers, composable aspects, and interpreters
- [x] thread that contract through programming surfaces, pass surfaces, and extension-island surfaces
- [x] add tests and example evidence for readable runnable stage artifacts after non-trivial rewrites
- [x] make committed-stage replay execute through `ProgramModule.run(...)` instead of payload-return wrappers
- [x] make pass contracts state Python renderability/executability preservation at committed stage boundaries
- [x] add a human-facing example under `examples/` that demonstrates IR definition, execution, and transformation without test-style payload assembly
- [x] start the typed IR-node substrate so the human-facing example is built on real typed IR objects rather than only dict-shaped semantic payloads
- [x] migrate one real public frontend (`htp.kernel`) onto the new `ProgramModule` intake path
- [x] replace dict-shaped aspect ownership for the committed-stage core with typed aspect wrappers
- [x] migrate `htp.routine`, `htp.wsp`, and `htp.csp` onto the `ProgramModule` intake path

## Code Surfaces

- producer: `htp/kernel.py`, `htp/routine.py`, `htp/wsp/`, `htp/csp/`, `htp/passes/`, `htp/pipeline/`, `htp/artifacts/`, `htp_ext/mlir_cse/`
- validator/binding: `htp/tools.py`, replay/package verification surfaces as needed
- tests: pipeline, replay, docs/process consistency
- docs: `docs/design/`, `docs/todo/`, `docs/in_progress/`, `docs/in_progress/design/`, `README.md` only if the contract wording needs refinement

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added
- [x] human-friendly IR-definition / execution / transformation example added under `examples/`
- [x] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract, failure mode, or regression.

## Documentation Plan

- [x] update `docs/design/` for implemented behavior
- [ ] update `docs/todo/` to remove or narrow the gap
- [x] update `docs/todo/` to narrow the AST-all-the-way gap
- [x] sync the validated redesign from `docs/in_progress/design/` into `docs/design/compiler_model.md`, `docs/design/programming_surfaces.md`, and `docs/design/artifacts_replay_debug.md`
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file and clear stale prior task file
2. write redesign docs under `docs/in_progress/design/`
3. land AST-all-the-way programming-surface and IR contract changes
4. land tests and example evidence
5. sync docs and TODO narrowing
6. rebase, review, and merge

## Review Notes

Reviewers should focus on whether the implementation really sharpens the joint
programming-surface and IR contract rather than only rephrasing docs, and
whether extension/MLIR boundaries still return to Python-owned global stage
artifacts.
