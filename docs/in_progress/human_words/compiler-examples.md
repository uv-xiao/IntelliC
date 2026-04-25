# Human Words: Compiler Examples

## Category

- Primary: Compiler Examples

## Timeline

- 2026-04-25 14:40 CST - Start strong example showcase PR
  > Let's open a new PR to make examples and tests strong. The current two examples are too naive. We need more challenging one. Also, the examples themselves should be self runner to show parse/print, semantic execution, and action features. Currently, the examples are underutilized to show features. This PR is a general one to add more challenge examples and show features by each.
  - Context: User requested a new feature PR after PR #71 merged the first executable IntelliC compiler slice.
  - Related: examples/
  - Related: tests/test_examples.py
  - Related: docs/in_progress/strong_example_showcase.md
  - Agent interpretation: Start a focused examples PR that strengthens examples and tests without broadening compiler implementation scope.

- 2026-04-25 14:40 CST - Keep examples standalone; tests reuse APIs
  > I think each exampel be runnable as its own module is enough. For the collective running, this is what tests need. Tests can reuse example codes. But they shoudn't just run example in a collective way.
  - Context: User clarified the example execution contract during design.
  - Related: examples/
  - Related: tests/test_examples.py
  - Related: docs/in_progress/strong_example_showcase.md
  - Agent interpretation: Do not add an aggregate example runner; make every example runnable as its own module and make tests call structured example APIs directly.

- 2026-04-25 14:40 CST - Stay within current compiler features
  > Stay within. For missed capabilities, they should be documented, not solved in this PR.
  - Context: User constrained scope after being asked whether the examples PR may extend compiler functionality.
  - Related: docs/in_progress/strong_example_showcase.md
  - Agent interpretation: Keep the PR focused on examples and tests. Record missing capabilities in the backlog instead of implementing them.

- 2026-04-25 14:40 CST - Maintain appendable example backlog
  > Good. But the PR should maintian a list to be appended when we found more cases are needed. For now, your proposed ones are OK. Are they from xDSL? We can take things from there.
  - Context: User approved the initial proposed examples and asked for an appendable list plus xDSL inspiration where useful.
  - Related: docs/in_progress/strong_example_showcase.md
  - Related: .repositories/xdsl/
  - Related: .repositories/llvm-project/
  - Agent interpretation: Maintain an example-case backlog with source inspiration, status, and missing capability notes; adapt xDSL/MLIR patterns rather than copying examples directly.

- 2026-04-25 16:58 local - Example README and sum baseline upgrade
  > examples/ need a readme to explain what each example does and want to show. Also, the old affine_tile.py can be removed (too easy), and the sum_to_n example should be improved to show more features (ir_parse/print, semantic execution, etc.)
  - Context: User requested a scoped extension to PR #72 after the strong example showcase was marked ready.
  - Related: examples/
  - Related: tests/test_examples.py
  - Related: docs/in_progress/strong_example_showcase.md
  - Agent interpretation: Add example-suite documentation, remove the simple affine_tile example, and make sum_to_n a first-class runnable example with structured evidence.
