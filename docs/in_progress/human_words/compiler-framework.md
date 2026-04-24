# Human Words: Compiler Framework

## Category

- Primary: Compiler Framework

## Timeline

- 2026-04-24 18:55 CST - Start complete IntelliC implementation PR
  > Let's start a new PR to implement the complete intellic according to the design in the last two PRs.
  - Context: User requested a new implementation pull request immediately after PR #70 merged the implementation-ready compiler design.
  - Related: docs/design/compiler_framework.md
  - Related: docs/design/compiler_syntax.md
  - Related: docs/design/compiler_semantics.md
  - Related: docs/design/compiler_passes.md
  - Related: docs/in_progress/complete_intellic_implementation.md
  - Agent interpretation: Start a feature PR for the complete first executable IntelliC implementation slice described by the last two design PRs, with scope kept verifiable through staged package, IR, dialect, parser, surface, semantic, action, and test milestones.

- 2026-04-24 19:05 CST - Prepare complete IntelliC implementation
  > Let's prepare for the implementation.
  - Context: User asked to prepare PR #71 for implementation after the draft implementation PR was opened.
  - Related: docs/in_progress/complete_intellic_implementation.md
  - Related: docs/design/compiler_framework.md
  - Related: docs/design/compiler_syntax.md
  - Related: docs/design/compiler_semantics.md
  - Related: docs/design/compiler_passes.md
  - Agent interpretation: Create an execution-ready implementation plan with batch order, file ownership, verification commands, and first code-slice boundary before writing compiler implementation code.

- 2026-04-24 19:25 CST - Keep examples outside package
  > Examples should be moved from intellic/ to examples/
  - Context: User corrected PR #71 implementation layout after end-to-end examples were added under the importable `intellic` package.
  - Related: examples/
  - Related: tests/test_examples.py
  - Agent interpretation: Move reusable example programs to top-level `examples/` so they remain project evidence rather than package internals, and update tests/docs to import from that location.
