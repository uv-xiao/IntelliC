# Feature Task: Compiler Framework Design

- Branch: `htp/clean`
- PR:
- Owner: Codex
- Status: in progress

## Goal

Design the clean IntelliC compiler framework from first principles, using MLIR,
xDSL, and `origin/htp/v0` as references while preserving IntelliC's human- and
LLM-friendly compiler development goal.

## Scope Checklist

- [x] Define input, output, and verification criteria
- [x] Update agent harness rules so design examples must become tests or evidence
- [x] Record reference readings under `docs/notes/`
- [x] Write the umbrella architecture decision draft under `docs/in_progress/design/`
- [x] Split syntax, semantics, and pass mechanism drafts into focused documents
- [x] Verify local harness policy and focused tests
- [x] Keep implemented design docs and todo state coherent

## Review Status

The compiler framework design drafts are not reviewed or approved. They record
current working direction and fix advice only; do not treat them as accepted
architecture until explicit human review approves them.

## Input

- User design direction for `Lang`, `Surface`, `IR`, `Sy`, and `Se`
- MLIR source/docs under `.repositories/llvm-project`
- xDSL source/docs under `.repositories/xdsl`
- Fjfj PLDI 2025 paper under `.references/acm-3729331.pdf`
- egg source under `.repositories/egg`
- egglog source under `.repositories/egglog`
- Previous architecture under `origin/htp/v0`
- Current clean-branch docs and harness rules

## Output

- Updated harness constraints requiring concrete design examples and
  tests/evidence mapping
- Source-reading note for the framework references
- In-progress umbrella design draft for the selected clean IntelliC compiler framework
- Focused in-progress design drafts for syntax, semantics, and passes

## Verification

- `python -m unittest tests.test_repo_harness`
- `python scripts/check_repo_harness.py`

## Tests

- Harness policy tests cover the new design-example requirements.
- Framework implementation tests are defined in the design draft and will be
  created when implementation starts.

## Docs

- `docs/notes/compiler_framework_sources.md`
- `docs/in_progress/design/compiler_framework.md`
- `docs/in_progress/design/compiler_syntax.md`
- `docs/in_progress/design/compiler_semantics.md`
- `docs/in_progress/design/compiler_passes.md`
- `docs/design/agent_harness.md`

## Closeout

Before merge, promote validated design content into `docs/design/`, close or
update `docs/todo/README.md`, and remove completed in-progress files.
