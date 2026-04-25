# Feature Task: Strong Example Showcase

- Branch: `examples/strong-showcase`
- PR: #72
- Owner: Codex
- Status: Implemented, locally verified, and synced to PR #72

## Goal

Make IntelliC examples strong enough to demonstrate the current compiler slice
instead of only proving that two small examples can be constructed.

Each example should be runnable as its own module and should expose reusable
Python APIs for tests. Tests should call those APIs directly rather than run a
single collective example command.

## Scope Checklist

- [x] Define input, output, and verification criteria
- [x] Write example-suite design and case backlog
- [x] Write implementation plan
- [x] Implement in coherent commits
- [x] Verify locally
- [x] Sync local `docs/todo/` and `docs/in_progress/` status
- [x] Sync PR body / remote state after review

## Input

- `examples/sum_to_n.py`
- `examples/README.md`
- `tests/test_examples.py`
- `docs/design/compiler_syntax.md`
- `docs/design/compiler_semantics.md`
- `docs/design/compiler_passes.md`
- Local xDSL and MLIR references under `.repositories/xdsl` and
  `.repositories/llvm-project`

## Output

- Challenging examples under `examples/` that each support
  `python -m examples.<module>`.
- Reusable example APIs that return structured demo evidence for tests.
- Tests that assert parser/printer idempotence, semantic results where current
  semantics support execution, action records, mutation evidence, and documented
  current gaps.
- A maintained example-case backlog that can be appended when new cases are
  needed.

## Design

### Example Contract

Each implemented example module must provide:

- a typed builder entry point, such as `build_example()` or a domain-specific
  `build_<case>()`;
- a `run_demo() -> ExampleRun` style entry point with structured evidence for
  tests;
- a `main()` entry point so `python -m examples.<module>` prints concise,
  human-readable sections:
  - canonical IR;
  - parse/print idempotence status;
  - semantic execution result when supported by the current compiler slice;
  - action or lowering evidence;
  - documented gaps when a desirable capability is outside this PR.

There should be no aggregate runner in this PR. Collective coverage belongs in
tests that import the example modules and call their APIs directly.

### Current-Feature Boundary

This PR stays within the current IntelliC feature set. If a stronger example
reveals a missing compiler capability, the example should document the gap or
record it in the backlog instead of implementing the missing compiler feature.

### Initial Implemented Cases

1. `examples/sum_to_n.py`
   - Source inspiration: the first executable compiler-slice example from PR
     #71.
   - IntelliC focus: canonical IR printing, parse/print idempotence, semantic
     execution for `sum_to_n(5) -> 10`, semantic trace counts, and action
     evidence.
   - Expected status: implemented in this PR.

2. `examples/scf_piecewise_accumulate.py`
   - Source inspiration: xDSL/MLIR SCF `if` and `for` examples from
     `.repositories/xdsl/docs/marimo/mlir_ir.py` and xDSL SCF interpreter tests.
   - IntelliC focus: nested `scf.if` inside `scf.for`, function-shaped IR,
     branch reachability evidence, parser/printer idempotence, and action
     records.
   - Expected status: implemented in this PR.

3. `examples/affine_stencil_tile.py`
   - Source inspiration: xDSL affine dialect/lower-affine tests and MLIR affine
     memory-access idioms.
   - IntelliC focus: affine min/max, multiple affine maps, scalar/vector memory
     accesses, affine object properties, memory-effect facts, and affine
     lowering evidence.
   - Expected status: implemented in this PR.

4. `examples/action_cleanup_pipeline.py`
   - Source inspiration: xDSL rewrite/canonicalization examples and transform
     tests.
   - IntelliC focus: deliberately optimizable IR that demonstrates
     canonicalization, CSE, sparse constant propagation, dead-code cleanup,
     mutation intents, applied mutation evidence, and final parse/print
     idempotence.
   - Expected status: implemented in this PR.

## Example Case Backlog

Append to this list when a new challenging case is discovered. Entries should
record source inspiration, features shown, status, and missing capability notes
when relevant.

| Case | Source Inspiration | Features Shown | Status | Notes |
| --- | --- | --- | --- | --- |
| `sum_to_n` | First executable compiler-slice example from PR #71 | canonical IR, parse/print, semantic execution, semantic trace counts, action evidence | implemented | Promoted from simple builder fixture to runnable structured example; old `affine_tile` example was removed as too small. |
| `scf_piecewise_accumulate` | xDSL/MLIR SCF `if`/`for` examples and interpreter tests | nested SCF, branch reachability, loop/action records, parse/print, documented semantic gap | implemented | Branch reachability/action records are implemented; `scf.if` concrete execution remains documented as a current gap. |
| `affine_stencil_tile` | xDSL affine dialect and lower-affine tests; MLIR affine memory-access idioms | affine maps, min/max, scalar/vector access facts, memory effects, lowering evidence | implemented | Affine fact and lowering evidence is implemented; concrete memory execution remains documented as a current gap. |
| `action_cleanup_pipeline` | xDSL rewrite/canonicalization examples and transform tests | canonicalization, CSE, SCCP-style facts, DCE, inline evidence, mutation evidence, semantic preservation | implemented | Final cleanup state is reported separately from historical call/liveness evidence; uses only currently implemented action behavior. |
| `scf_while_state_machine` | MLIR/xDSL SCF while examples | while/condition/after region contracts and execution evidence | deferred | Document as a future case if current semantic execution is not sufficient. |
| `affine_loop_nest_execution` | MLIR affine loop examples | nested affine loop execution and access legality | deferred | Current affine support records facts/lowering evidence but does not execute affine loops. |
| `vector_compute_pipeline` | MLIR vector examples | vector compute semantics and transformations | deferred | Current vector support is type/access-oriented, not full vector computation. |

## Verification Criteria

- `python -m unittest tests/test_examples.py` passes.
- `python -m unittest discover -s tests` passes.
- `python scripts/check_repo_harness.py` passes.
- `python -m examples.sum_to_n` exits 0 and prints canonical IR,
  parse/print status, semantic result, semantic trace counts, and action
  evidence.
- `python -m examples.scf_piecewise_accumulate` exits 0 and prints canonical IR,
  parse/print status, branch reachability/action evidence, and the documented
  semantic execution gap.
- `python -m examples.affine_stencil_tile` exits 0 and prints canonical IR,
  parse/print status, affine access facts, and lowering evidence.
- `python -m examples.action_cleanup_pipeline` exits 0 and prints canonical IR,
  parse/print status, action records, mutation evidence, and final IR.
- Tests import each example module and assert structured evidence directly.

## Tests

Completed local verification commands:

```bash
python -m unittest tests/test_examples.py
python -m unittest discover -s tests
python scripts/check_repo_harness.py
python -m examples.sum_to_n
python -m examples.scf_piecewise_accumulate
python -m examples.affine_stencil_tile
python -m examples.action_cleanup_pipeline
```

## Implementation Verification

Task 5 verification commands:

```bash
python -m unittest tests/test_examples.py
python -m unittest discover -s tests
python scripts/check_repo_harness.py
python -m examples.sum_to_n
python -m examples.scf_piecewise_accumulate
python -m examples.affine_stencil_tile
python -m examples.action_cleanup_pipeline
git diff --check
```

Observed results from the Task 5 local verification run:

- `python -m unittest tests/test_examples.py`: exit 0; `Ran 7 tests in 0.023s`;
  `OK`.
- `python -m unittest discover -s tests`: exit 0; `Ran 139 tests in 0.124s`;
  `OK`.
- `python scripts/check_repo_harness.py`: exit 0; `repo harness policy passed`.
- `python -m examples.sum_to_n`: exit 0; printed `canonical_ir:`,
  `parse_print_idempotent: true`, `semantic_result: (10,)`,
  `LoopIteration: 5`, `Evaluated: 14`, actions including
  `canonicalize-greedy` and `loop-invariant-code-motion`, and
  `ValueConcrete: 3`.
- `python -m examples.scf_piecewise_accumulate`: exit 0; printed
  `canonical_ir:`, `parse_print_idempotent: true`, actions
  `verify-structure, sparse-constant-propagation, loop-invariant-code-motion`,
  `BranchReachability: 2`, `ThenReachable: 1`, `ElseReachable: 1`, and the
  documented `scf.if concrete execution is not implemented` gap.
- `python -m examples.affine_stencil_tile`: exit 0; printed `canonical_ir:`,
  `parse_print_idempotent: true`, actions
  `verify-structure, common-subexpression-elimination, lower-affine-to-scf`,
  `UniqueAffineAccess: 7`, `UniqueMemoryEffect: 7`, `ReadAccess: 4`,
  `WriteAccess: 3`, `UniqueAffineExpansion: 9`, and the documented
  `affine concrete memory execution is not implemented` gap.
- `python -m examples.action_cleanup_pipeline`: exit 0; printed
  `canonical_ir:`, `parse_print_idempotent: true`, `semantic_result: (5,)`,
  actions `verify-structure, canonicalize-greedy,
  common-subexpression-elimination, sparse-constant-propagation,
  symbol-dce-and-dead-code, inline-single-call, symbol-dce-and-dead-code`,
  `MutationApplied: 6`, `MutationRejected: 0`, historical call/liveness
  evidence, and a `final_ir:` section with `FinalFuncCallOps: 0`,
  `FinalIdentitySymbols: 0`, `FinalDeadPrivateSymbols: 0`, and
  `FinalZeroConstants: 0`.
- `git diff --check`: exit 0; no whitespace errors.

## Docs

- Keep this task file as the maintained example backlog for this PR.
- If examples expose missing compiler capabilities, document them in the
  backlog and do not implement those capabilities in this PR.
- At closeout, archive the PR human-word records under `docs/archive/`.

## Closeout

Before merge:

- Mark implemented backlog cases as `implemented`.
- Update `docs/todo/README.md`.
- Archive completed task and human-word records when merging the PR.
