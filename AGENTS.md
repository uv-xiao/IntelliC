# HTP Repository Guidance

This file is the operating contract for agents and contributors working in this repository.

## 1. Branch and task lifecycle

`htp/dev` is the stable branch. Do not develop features on it.

For every feature-sized change:

1. start from `htp/dev`
2. choose a feature-sized gap from `docs/todo/README.md`
3. create a branch named `htp/feat-<topic>`
4. create a task file under `docs/in_progress/` using `docs/in_progress/TEMPLATE.md`
5. make that task-file creation its own first commit
6. open a PR from the feature branch to `htp/dev`
7. land implementation as additional commits on that PR
8. before merge:
   - update `docs/design/` for what is now implemented
   - update `docs/todo/README.md` and any active `docs/todo/` feature file if one exists
   - remove the corresponding file from `docs/in_progress/`
   - rebase on current `htp/dev`
   - verify locally and wait for green CI

A feature task is not a tiny fix. It should be large enough to justify a PR with multiple commits.

## 2. Start-of-task protocol

Before editing:

1. run `git status --short --branch`
2. identify the exact contract surfaces being changed
3. read:
   - `.agent/rules/core-development.md`
   - `.agent/rules/docs-and-artifacts.md`
   - `.agent/rules/testing-and-verification.md`
4. if touching a backend, binding, runtime, replay path, artifact layout, or extension seam, read the corresponding doc in `docs/design/` and the relevant example-local `examples/**/README.md`

Do not begin with speculative edits.

## 3. Documentation structure

The `docs/` tree is strict.

- `docs/design/`
  - implemented behavior only
  - must reference real code paths
  - `README.md` is the index and architecture entrypoint
  - broad topic documents live under `docs/design/`
- `docs/todo/`
  - unimplemented or partial features only
  - `README.md` is the summary checklist for remaining feature work
  - detailed feature files appear here only while a concrete future gap is still open
- `docs/in_progress/`
  - active feature-branch task files only
  - one file per feature PR
- `docs/story.md`
  - the final intended framework story and target envelope
- `docs/reference/`, `docs/research/`
  - retained as supporting corpora

Do not leave stale duplicates across `design`, `todo`, and `in_progress`.

## 4. Non-negotiable architecture rules

- Python-space is the canonical compiler form.
- Stage programs must remain runnable in `sim`, or fail with a structured replay diagnostic.
- Emitted artifacts are part of the public contract.
- Bindings must report malformed package state through structured diagnostics, not crashes.
- MLIR is an extension mechanism, not a native semantic owner of the core compiler.
- Extension-owned functionality belongs under `htp_ext/` unless the design explicitly places it in core.
- Ampere and Blackwell are profiles of the same `nvgpu` backend.

If a requested change weakens one of these rules, stop and resolve the conflict before coding.

## 5. Layering and ownership

Keep responsibilities separated:

- `htp/ir/`: identity, maps, staged IR state
- `htp/artifacts/`: stage/manifest emission and validation
- `htp/passes/`: pass contracts, pass execution, pass outputs
- `htp/runtime/`: replay/runtime primitives only
- `htp/bindings/`: validate/build/load/run/replay integration
- `htp/backends/<backend>/`: backend lowering and artifact emission
- `htp_ext/`: optional extension-owned functionality

Do not move backend-specific or MLIR-specific logic into unrelated layers.

## 6. Contract-first development

When changing a contract surface, update all of these together:

1. producer code
2. validator/binding logic
3. tests for valid and malformed cases
4. docs for semantics and file layout

Contract surfaces include:

- `manifest.json`
- stage graph records
- `analysis/index.json`
- `ids/*.json`
- `maps/*.json`
- backend codegen indices
- toolchain manifests
- replay diagnostics

Never add a new emitted field without deciding who owns it, whether it is normative, how it is validated, and which test asserts it.

## 7. Example and test authoring rules

HTP is Python-AST-centric. That does **not** mean user programs should be presented as raw data blobs.

Rules:

- Examples and high-level tests must look like human-written Python programs.
- Do not build flagship examples around giant top-level dict constants such as `FOO_PROGRAM = {...}`.
- Prefer:
  - decorator-based or traced Python authoring surfaces,
  - ordinary Python functions and control flow,
  - frontend authoring surfaces such as `htp.kernel`, `htp.routine`, `htp.wsp`, and `htp.csp`,
  - or small local builders only when testing a low-level contract directly.
- Raw dict payloads are acceptable only for low-level contract tests that intentionally exercise emitted/package data shapes.
- Avoid public authoring styles that feel like constructor soup. If a flagship
  example requires stacking many explicit spec constructors just to say
  something simple, the surface is not good enough yet.
- Calibrate the flagship authoring experience against `references/pypto/` and
  `references/arknife/`. HTP should be at least as readable as those examples.
- Calibrate scheduling/dataflow authoring against
  `references/triton-distributed-knowingnothing/python/little_kernel/` as well;
  examples that are technically correct but syntactically ugly still fail review.

Difficulty rules:

- Examples must be hard enough to demonstrate real functionality.
- A flagship example should exercise at least one substantial capability:
  - non-trivial scheduling,
  - protocol/dataflow behavior,
  - backend discharge,
  - extension composition,
  - or multi-stage artifact evidence.
- Keep trivial smoke cases in tests, not as the main public examples.
- When choosing example scope, consult `references/` and existing real systems before settling for an overly easy case.
- Use `references/pypto/examples/language/{beginner,intermediate,llm_models}/`
  and `references/arknife/tests/python/` as the minimum bar for flagship
  example ambition.
- Review public programming surfaces and flagship examples for human
  friendliness and syntax prettiness explicitly. If the surface reads like
  constructor soup, nested raw payload assembly, or non-native Python, the PR
  is not done yet even if the tests pass.
- WSP flagship examples must show meaningful task roles, dependency edges, and
  stage plans; CSP flagship examples must show meaningful process roles and
  protocol-local steps. A prettier wrapper around a shallow single-task example
  does not clear review.

## 8. Code readability and documentation rules

All new or substantially changed code must be human-readable and documented.

Specific requirements:

- public modules must have a short module docstring when the file owns a contract or non-obvious mechanism
- public classes, dataclasses, and public functions should have docstrings when their role is not immediately obvious from the name alone
- complex transformations, legality checks, or adapter flows need short comments describing:
  - invariants,
  - non-obvious data contracts,
  - or why a branch exists
- do not add comment noise for obvious statements
- use explicit, semantic names; avoid opaque abbreviations and single-letter names unless mathematically standard
- examples and tests should read top-to-bottom without forcing the reader to reconstruct hidden state from globals

## 9. Testing and CI discipline

Every behavior change must include focused tests.

Minimum expectation:

- one happy-path test
- one malformed-input or contract-violation test
- one regression test for the actual bug or gap being addressed

Quality rules:

- do not add redundant, low-signal, or trivially duplicative tests
- each added test must protect a concrete contract, failure mode, or regression
- if several tests cover the same path with no new signal, collapse them

Verification rules:

- preferred: `pixi run verify`
- fallback only when Pixi is unavailable:
  - `python -m pip install --user --upgrade pip setuptools wheel`
  - `python -m pip install -e '.[dev]'`
  - `pytest`
  - `pre-commit run --all-files`
- a PR is not ready until all configured CI checks are green
- do not fix CI by weakening coverage, assertions, or jobs unless the repository contract itself has intentionally changed and docs/tests are updated consistently

## 10. Review checklist before commit

Check all of the following:

- no contract bypass was introduced
- backend selection still works when markers overlap
- diagnostics still expose actual manifest/artifact values
- generated fixtures still match current emitters
- new files were placed in the correct layer
- `docs/design/`, `docs/todo/`, and `docs/in_progress/` are consistent with the branch state
- public programming surfaces and flagship examples are readable without
  reconstructing hidden payload structure

## 11. Prohibited patterns

Do not:

- add MLIR dependencies to the HTP core package
- treat `build/toolchain.json` as a unique backend marker without context
- validate only the happy path
- emit unreferenced artifacts
- make stages non-runnable in `sim` without structured diagnostics
- leave formatting or verification drift in the branch
- develop new features directly on `htp/dev`
- leave a completed feature documented only in `docs/in_progress/`

## 12. Expected handoff

A complete handoff states:

- what changed
- why it changed
- which contracts were affected
- exact verification commands run
- PR / CI status, including whether all required checks are green
- any remaining gap or deferred scope

When the handoff is a PR, the PR body must use the repository template headings:

- `Summary`
- `Why`
- `Contracts`
- `Tests`
- `CI`
- `Scope`
- `Reviewer Notes`
