# HTP Repository Guidance

This file is the default operating contract for any agent or contributor working in this repository.

## 1. Start-of-task protocol

Before editing:

1. Run `git status --short --branch`.
2. Identify the exact files and contract surfaces affected.
3. Read the relevant local rules in:
   - `.agent/rules/core-development.md`
   - `.agent/rules/docs-and-artifacts.md`
   - `.agent/rules/testing-and-verification.md`
4. If touching a backend, binding, runtime, replay path, artifact layout, or extension seam, read the matching design doc under `docs/design/impls/`.

Before starting feature work, verify the branch:

- `htp/dev` is the stable branch and should stay CI-passed.
- New feature work must happen on a feature branch named `htp/feat-<topic>`.
- Merge back into `htp/dev` through a PR-style review flow after tests and hooks pass.
- A feature branch is not ready for review or handoff until its PR is in a state that passes all configured CI checks.
- PR automation now enforces:
  - base branch must be `htp/dev`
  - head branch must start with `htp/feat-`
  - code-backed or `docs/design/` changes must update `docs/future/gap_checklist.md`
- Every PR description must follow `.github/pull_request_template.md`.
- Do not open or update a PR with an ad-hoc or low-signal description; rewrite it to match the template.
- Do not land exploratory or half-finished feature work directly on `htp/dev`.

Do not begin with speculative edits.

## 2. Non-negotiable architecture rules

- Python-space is the canonical compiler form.
- Stage programs must remain runnable in `sim`, or fail with a structured replay diagnostic.
- Emitted artifacts are part of the public contract.
- Bindings must report malformed package state through structured diagnostics, not crashes.
- MLIR is an extension mechanism, not a native semantic owner of the core compiler.
- Extension-owned functionality belongs under `htp_ext/` unless the design explicitly places it in core.
- Ampere and Blackwell are profiles of the same `nvgpu` backend.

If a requested change weakens one of these rules, stop and resolve that conflict explicitly before coding.

## 3. Layering and file ownership

Keep responsibilities separated:

- `htp/ir/`: identity, maps, staged IR state
- `htp/artifacts/`: stage/manifest emission and validation
- `htp/passes/`: pass contracts, pass execution, pass outputs
- `htp/runtime/`: replay/runtime primitives only
- `htp/bindings/`: validate/build/load/run/replay integration
- `htp/backends/<backend>/`: backend lowering and artifact emission
- `htp_ext/`: optional extension-owned functionality

Do not move backend-specific or MLIR-specific logic into unrelated layers.

## 4. Contract-first development

When changing a contract surface, update all of these together:

1. producer code
2. validator/binding logic
3. tests for valid and malformed cases
4. documentation if semantics or file layout changed

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

## 5. Coding rules

- Keep patches narrow and local.
- Fix root causes at contract boundaries instead of adding downstream compensations.
- Use explicit types on public or contract-facing APIs.
- Prefer deterministic ordering and stable emitted payloads.
- Prefer explicit diagnostics with stable `code` and concrete `detail`.
- Avoid silent fallback.
- Avoid hidden global state except the intentional default replay runtime.
- Reuse repo conventions instead of inventing one-off mechanisms.

## 6. Testing rules

Every behavior change must include focused tests.

Minimum expectation:

- one happy-path test
- one malformed-input or contract-violation test
- one regression test for the actual bug being fixed

Specific expectations:

- bindings: malformed manifests, missing files, selection logic
- backends: emitted file contract, manifest parity, binding validation
- runtime: structured replay diagnostics
- extensions: remain out of core and replay in `sim`

Quality rules:

- Do not add tests that only restate trivial implementation details without protecting a contract, failure mode, or
  regression.
- Do not inflate test counts with redundant variants that exercise the same behavior through the same path.
- Prefer a small set of high-signal tests that defend the contract surface and likely failure modes.
- When adding a test, be able to state exactly which contract, bug, or regression it protects.
- If a test becomes obsolete because the contract moved, update or remove it deliberately; do not keep low-value tests
  as noise.

Before claiming completion, run:

- `pixi run verify`

Fallback only when Pixi is unavailable:

- `python -m pip install -e '.[dev]'`
- `pytest`
- `pre-commit run --all-files`

## 6.1 Environment rules

- `pixi.toml` is the authoritative development and CI environment contract.
- Keep `pixi.toml`, `pyproject.toml`, and `.github/workflows/ci.yml` aligned.
- If code under `htp/`, `htp_ext/`, or `examples/` imports a dependency at runtime, it must live in
  `[project].dependencies`, not only in a dev-only list.
- Use the named Pixi environments when changing CI version coverage:
  - `py311` is the default development environment
  - `py310` and `py311` are the CI test environments
- Do not add a second disconnected setup path for CI.
- Do not weaken CI or remove checks just to make a failure disappear.
- When CI fails, first assume the failure exposed a real contract, fixture, environment, or test issue and resolve the
  root cause.
- Any CI or test change must make correctness stronger or clearer, not merely easier to pass.

## 7. Documentation rules

- Update docs when artifact layout or contract meaning changes.
- Keep docs aligned with the actual emitted paths and validation behavior.
- Prefer focused edits to existing design docs over ad-hoc markdown.
- Keep the docs split strict:
  - `docs/design/` = implemented, code-backed behavior only
  - `docs/future/` = not implemented yet, design/research/roadmap material
- Do not place unimplemented features under `docs/design/`.

## 8. Review checklist before commit

Check all of the following:

- no contract bypass was introduced
- backend selection still works when markers overlap
- diagnostics still expose actual manifest/artifact values
- pytest module names are unique enough to avoid import collisions
- generated fixtures still match current emitters
- new files were placed in the correct layer

## 9. Prohibited patterns

Do not:

- add MLIR dependencies to the HTP core package
- treat `build/toolchain.json` as a unique backend marker without context
- validate only the happy path
- emit unreferenced artifacts
- make stages non-runnable in `sim` without structured diagnostics
- leave formatting or verification drift in the branch
- develop new features directly on `htp/dev`

## 10. Expected handoff

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
