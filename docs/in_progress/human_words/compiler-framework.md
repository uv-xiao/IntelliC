# Human Words: Compiler Framework

## Category

- Primary: Compiler Framework

## Timeline

- 2026-04-24 11:17 CST - Start implementation-ready design PR
  > Let's start a new PR, where we need to make the full implementation-ready design clear.
  - Context: User requested a new PR focused on turning the accepted compiler architecture into implementation-ready design.
  - Related: docs/design/compiler_framework.md
  - Related: docs/design/compiler_syntax.md
  - Related: docs/design/compiler_semantics.md
  - Related: docs/design/compiler_passes.md
  - Related: docs/in_progress/implementation_ready_compiler_design.md
  - Agent interpretation: Create a feature branch and design task that clarifies implementation order, concrete module contracts, invariants, examples, and verification mapping before implementation begins.

- 2026-04-24 15:22 CST - Require challenging implementation design examples
  > For examples, we need to pick those relatively hard or challenging to make things truely work. Let's go ahead to have detailed implementation design.
  - Context: User refined PR #70 to require challenging examples that stress implementation readiness instead of only easy proof points.
  - Related: docs/design/compiler_framework.md
  - Related: docs/design/compiler_syntax.md
  - Related: docs/design/compiler_semantics.md
  - Related: docs/design/compiler_passes.md
  - Related: docs/in_progress/design/implementation_ready_compiler_design.md
  - Agent interpretation: Use harder examples such as region control flow, loop-carried values, TraceDB facts, and action-driven mutation to force detailed implementation contracts and verification evidence.

- 2026-04-24 16:11 CST - Require affine and full SCF implementation design
  > Review and improve the design documents further to make them concrete enough for implementation. One very important dialect is affine, which we need to support well. Also, we need to support all scf.
  - Context: User refined PR #70 to require full SCF coverage and strong affine dialect support in the implementation-ready design.
  - Related: docs/design/compiler_framework.md
  - Related: docs/design/compiler_syntax.md
  - Related: docs/design/compiler_semantics.md
  - Related: docs/design/compiler_passes.md
  - Related: docs/in_progress/design/implementation_ready_compiler_design.md
  - Agent interpretation: Review accepted compiler design for implementation gaps, promote affine from future/nice-to-have to a first-class dialect family, and define full SCF syntax/semantics/action coverage rather than only scf.for.

- 2026-04-24 16:29 CST - Fill implementation design gaps and choose first passes
  > Fill the missing things. You also need to decide a set of passes to be implemented in the first slice.
  - Context: User asked to address the review findings for PR #70 and make an explicit first-slice pass selection.
  - Related: docs/design/compiler_syntax.md
  - Related: docs/design/compiler_semantics.md
  - Related: docs/design/compiler_passes.md
  - Related: docs/design/compiler_framework.md
  - Related: docs/in_progress/design/implementation_ready_compiler_design.md
  - Agent interpretation: Define the missing memref/vector substrate for affine, concrete scf.forall operation contracts, typed affine legality records, and a selected first-slice pass/action set.

- 2026-04-24 16:45 CST - Prefer shared MLIR/xDSL passes for first slice
  > You should pick the important passes from MLIR/xDSL (somehow, the shared ones are more important) to implement. They should cover the dialects.
  - Context: User refined PR #70 first-slice pass selection after the previous bespoke pass list.
  - Related: docs/design/compiler_passes.md
  - Related: docs/design/compiler_framework.md
  - Related: docs/in_progress/design/implementation_ready_compiler_design.md
  - Agent interpretation: Revise the first-slice pass set to prioritize important shared/common MLIR and xDSL pass families while still covering builtin, func, arith, scf, affine, memref, and vector contracts.
