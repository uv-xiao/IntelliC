# Feature Task: Strong Example Showcase

- Branch: `examples/strong-showcase`
- PR: unopened
- Owner: Codex
- Status: Design approved; implementation plan pending

## Goal

Make IntelliC examples strong enough to demonstrate the current compiler slice
instead of only proving that two small examples can be constructed.

Each example should be runnable as its own module and should expose reusable
Python APIs for tests. Tests should call those APIs directly rather than run a
single collective example command.

## Scope Checklist

- [x] Define input, output, and verification criteria
- [x] Write example-suite design and case backlog
- [ ] Implement in coherent commits
- [ ] Verify locally
- [ ] Sync `docs/design/`, `docs/todo/`, and `docs/in_progress/`

## Input

- `examples/sum_to_n.py`
- `examples/affine_tile.py`
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

1. `examples/scf_piecewise_accumulate.py`
   - Source inspiration: xDSL/MLIR SCF `if` and `for` examples from
     `.repositories/xdsl/docs/marimo/mlir_ir.py` and xDSL SCF interpreter tests.
   - IntelliC focus: nested `scf.if` inside `scf.for`, function execution,
     loop trace evidence, parser/printer idempotence, and action records.
   - Expected status: implemented in this PR.

2. `examples/affine_stencil_tile.py`
   - Source inspiration: xDSL affine dialect/lower-affine tests and MLIR affine
     memory-access idioms.
   - IntelliC focus: affine min/max, multiple affine maps, scalar/vector memory
     accesses, affine object properties, memory-effect facts, and affine
     lowering evidence.
   - Expected status: implemented in this PR.

3. `examples/action_cleanup_pipeline.py`
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
| `scf_piecewise_accumulate` | xDSL/MLIR SCF `if`/`for` examples and interpreter tests | nested SCF, semantic execution, loop trace records, parse/print, action evidence | planned | Current semantics should execute `func`, `arith`, and `scf.for`; branch support must be verified before implementation. |
| `affine_stencil_tile` | xDSL affine dialect and lower-affine tests; MLIR affine memory-access idioms | affine maps, min/max, scalar/vector access facts, memory effects, lowering evidence | planned | Concrete memory execution is out of scope unless already supported. |
| `action_cleanup_pipeline` | xDSL rewrite/canonicalization examples and transform tests | canonicalization, CSE, SCCP-style facts, DCE, mutation evidence, final IR | planned | Must use only currently implemented IntelliC action behavior. |
| `scf_while_state_machine` | MLIR/xDSL SCF while examples | while/condition/after region contracts and execution evidence | deferred | Document as a future case if current semantic execution is not sufficient. |
| `affine_loop_nest_execution` | MLIR affine loop examples | nested affine loop execution and access legality | deferred | Current affine support records facts/lowering evidence but does not execute affine loops. |
| `vector_compute_pipeline` | MLIR vector examples | vector compute semantics and transformations | deferred | Current vector support is type/access-oriented, not full vector computation. |

## Verification Criteria

- `python -m unittest tests/test_examples.py` passes.
- `python -m unittest discover -s tests` passes.
- `python scripts/check_repo_harness.py` passes.
- `python -m examples.scf_piecewise_accumulate` exits 0 and prints canonical IR,
  parse/print status, semantic result, and action evidence.
- `python -m examples.affine_stencil_tile` exits 0 and prints canonical IR,
  parse/print status, affine access facts, and lowering evidence.
- `python -m examples.action_cleanup_pipeline` exits 0 and prints canonical IR,
  parse/print status, action records, mutation evidence, and final IR.
- Tests import each example module and assert structured evidence directly.

## Tests

Planned focused verification:

```bash
python -m unittest tests/test_examples.py
python -m unittest discover -s tests
python scripts/check_repo_harness.py
python -m examples.scf_piecewise_accumulate
python -m examples.affine_stencil_tile
python -m examples.action_cleanup_pipeline
```

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
