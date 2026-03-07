---
name: init
description: Strict HTP initialization and coding guidance for any agent starting work in this repository
---

# HTP `/init`

Read this before making any change. These rules are strict. If a requested change conflicts with them, surface the conflict explicitly and resolve it before editing code.

## 1. Session start protocol

1. Confirm you are operating in the HTP repo root.
2. Run `git status --short --branch` before editing anything.
3. Identify the exact files and contracts affected.
4. Read the relevant local guidance in this order:
   - `.agent/rules/core-development.md`
   - `.agent/rules/docs-and-artifacts.md`
   - `.agent/rules/testing-and-verification.md`
5. If touching a backend, binding, artifact, runtime, or replay path, read the matching design doc under `docs/design/impls/`.
6. If the task changes behavior, define the verification target before implementation.

Do not start with speculative edits.

## 2. Non-negotiable architectural invariants

These are repository-level invariants, not suggestions.

- Python-space is the canonical compiler form.
- Stage programs must remain runnable in `sim`, or fail with a structured replay diagnostic.
- Emitted artifacts are contracts, not incidental output.
- Bindings must validate malformed package state with structured diagnostics, not crashes.
- Extension-owned logic must stay outside the HTP core package unless the design explicitly places it in core.
- MLIR is an extension mechanism, not a native semantic owner.
- Ampere and Blackwell are profiles of one `nvgpu` backend, not separate backends.

Any change that weakens these invariants is incorrect unless the design docs are updated first and the change is explicitly approved.

## 3. File ownership and layering rules

Respect these boundaries:

- `htp/ir/`: identity, maps, staged IR state only
- `htp/artifacts/`: manifest/stage layout and validation only
- `htp/passes/`: pass contracts, pass execution, and pass outputs only
- `htp/runtime/`: replay/runtime primitives only
- `htp/bindings/`: package validation, build/load/run/replay API only
- `htp/backends/<backend>/`: backend-specific lowering and artifact emission only
- `htp_ext/`: optional extension-owned functionality only

Do not leak backend-specific semantics into `htp/runtime/`.
Do not put MLIR-specific logic into `htp/`.
Do not make `htp/bindings/api.py` depend on accidental file layout assumptions beyond declared artifact markers.

## 4. Contract-first editing rules

When changing any contract surface, update all of the following together:

1. producer code
2. validator or binding logic
3. tests for valid and malformed cases
4. docs if the contract meaning changed

Contract surfaces include:

- `manifest.json`
- stage records
- `analysis/index.json`
- `ids/*.json`
- `maps/*.json`
- backend codegen indices
- toolchain manifests
- replay diagnostics

Never add a new emitted field without deciding:

- who owns it
- whether it is normative
- how it is validated
- which test asserts it

## 5. Coding rules

- Keep patches narrow. Solve the root contract problem; do not add compensating hacks downstream.
- Prefer explicit functions and small helpers over hidden conditionals.
- Use type annotations on public or contract-facing APIs.
- Prefer deterministic data layout and ordering.
- Keep diagnostics machine-consumable:
  - stable `code`
  - concrete `detail`
  - explicit field references where applicable
- Avoid silent fallback.
- Avoid hidden global state, except the intentional replay default runtime.
- Do not introduce one-off conventions if an existing repo convention can be extended cleanly.

## 6. Testing rules

Every behavior change needs focused tests first or alongside the change.

Minimum expectations:

- happy-path test
- malformed-input or contract-violation test
- regression test for the exact bug being fixed

When touching:

- `htp/bindings/*`: test malformed manifests, missing files, and selection logic
- `htp/backends/*`: test emitted files, manifest metadata, and binding validation
- `htp/runtime/*`: test structured diagnostics and replay behavior
- `htp_ext/*`: test that the extension stays outside core and still replays in `sim`

Before claiming success, run:

- `pytest`
- `pre-commit run --all-files`

If either fails, fix or explicitly explain why the failure is unrelated.

## 7. Documentation rules

Update docs when contracts or emitted artifacts change.

At minimum:

- if a backend artifact layout changes, update the corresponding `docs/design/impls/*.md`
- if a replay or diagnostic contract changes, update the relevant design/debuggability docs
- if a new extension seam is added, document why it belongs in core vs `htp_ext`

Do not leave docs describing obsolete file layouts.

## 8. Review checklist before commit

Before committing, verify:

- no hidden contract bypass was introduced
- backend selection order is robust against overlapping artifact markers
- diagnostics still report the actual manifest/artifact values
- tests use unique module basenames to avoid pytest import collisions
- generated fixtures match the current emitters
- new files are placed in the correct layer

If a change touches selection logic or shared manifests, assume cross-backend regressions are possible and test them explicitly.

## 9. Prohibited patterns

Do not:

- add MLIR dependencies to the HTP core package
- encode backend behavior through unnamed magic strings scattered across files
- validate only the happy path
- emit artifacts that are not referenced or testable
- treat `build/toolchain.json` as a unique backend marker without additional context
- make stages non-runnable in `sim` without structured replay diagnostics
- leave formatting or test drift in the branch

## 10. Expected final handoff

A complete handoff includes:

- what changed
- why it changed
- which contracts were affected
- exact verification commands run
- any remaining gap or deferred scope

Do not claim “done” without evidence.
