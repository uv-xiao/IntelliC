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

- 2026-04-24 23:40 CST - Implement missing merge blockers with subagents
  > Implement missing things with $superpowers:subagent-driven-development
  - Context: Final review for PR #71 found merge blockers in full SCF support, direct `func.call` semantics, and concrete action/pass behavior.
  - Related: docs/in_progress/complete_intellic_implementation.md
  - Related: docs/in_progress/complete_intellic_implementation_plan.md
  - Related: tests/dialects/
  - Related: tests/test_semantics.py
  - Related: tests/actions/
  - Agent interpretation: Use the subagent-driven implementation workflow to close the blockers with implementation, spec review, code-quality review, and fresh verification evidence before PR merge readiness.

- 2026-04-25 00:45 CST - Harden package and test organization
  > We need to improve file organization. Common infra things should be put under intellic/ir. But the concrete passes should be put under intellic/actions/, while the specific dialect defination should be put under intellic/dialects/. And we should avoid very large test files. Instead, we should create sub-folders. Also, in tests, we should assert golden IR printing and "original == parsed-printed" assertions. This is an important step to make the project strong.
  - Context: User requested structural hardening for PR #71 after the implementation and final-review blocker fixes were complete.
  - Related: intellic/dialects/
  - Related: intellic/actions/
  - Related: tests/actions/
  - Related: tests/dialects/
  - Related: tests/parser/
  - Agent interpretation: Move concrete definitions out of common IR infrastructure, split monolithic tests into focused subfolders, and strengthen parser/printer tests with golden text plus parse-print idempotence.

- 2026-04-25 11:52 CST - Fix all final merge review issues
  > all issues need to be fixed.
  - Context: User accepted the final merge review findings and directed all blockers to be fixed before merge.
  - Related: intellic/ir/syntax/printer.py
  - Related: intellic/ir/parser/parser.py
  - Related: intellic/ir/syntax/verify.py
  - Related: intellic/dialects/scf.py
  - Related: tests/parser/test_golden_ir.py
  - Related: tests/test_examples.py
  - Agent interpretation: Close all merge review blockers: MLIR-like canonical IR printing/parsing, stale use verification, SCF terminator strictness, and robust golden/idempotent example tests.
