# Feature Task: Complete IntelliC Implementation Slice

- Branch: `implement/complete-intellic-slice`
- PR: #71
- Owner: Codex
- Status: Active

## Goal

Implement the complete first executable IntelliC compiler slice described by the
accepted compiler design from the last two PRs.

For this PR, "complete IntelliC" means the full verifiable slice promised by the
accepted design: native package scaffolding, `Sy` syntax objects, first-slice
dialects, canonical parser/printer, Python construction surfaces, `Se`
semantics over `TraceDB`, shared-pass-style actions, and examples/tests that
prove the system works end to end.

## Scope Checklist

- [x] Define input, output, and verification criteria
- [x] Implement minimal package and verification tooling
- [x] Implement `intellic.ir.syntax` identity, ownership, use-list, builder, and
  verifier contracts
- [x] Implement first-slice dialects: builtin, func, arith, full SCF contracts,
  affine contracts, and minimal memref/vector type substrate
- [x] Implement canonical parser/printer round-trip for selected generic/custom
  forms
- [x] Implement Python construction surfaces for module/function/arith/SCF/affine
  examples
- [x] Implement `TraceDB`, semantic registry, concrete interpreter, and selected
  first-slice semantic definitions
- [x] Implement shared-pass-style actions and gates selected from MLIR/xDSL:
  canonicalization, CSE, SCCP-style propagation, symbol/dead-code cleanup,
  single-call inlining, LICM, affine lowering/normalization, and pending-record
  gate
- [x] Add examples and tests for `sum_to_n`, affine tiled access facts, parser
  round-trip, construction evidence, semantic execution, and action evidence
- [x] Verify locally
- [x] Sync `docs/design/`, `docs/todo/`, and `docs/in_progress/`

## Input

- `docs/design/compiler_framework.md`
- `docs/design/compiler_syntax.md`
- `docs/design/compiler_semantics.md`
- `docs/design/compiler_passes.md`
- `docs/notes/compiler_framework_sources.md`
- Local reference checkouts under `.repositories/xdsl` and
  `.repositories/llvm-project`

## Output

- Importable `intellic` package with the first executable compiler slice.
- Tests that validate the accepted design contracts.
- Example programs that demonstrate construction, parsing, printing, semantic
  execution, and action evidence.
- Updated task/TODO docs and archived human-word records at PR closeout.

## Implementation Plan

Detailed execution plan: `docs/in_progress/complete_intellic_implementation_plan.md`.

1. Package foundation:
   create `pyproject.toml` or equivalent minimal project metadata, `intellic/`,
   and baseline tests/import checks without adding external dependencies.
2. Syntax core:
   implement ids, locations, immutable types/attributes, values/use lists,
   operations, regions/blocks, builder insertion, and structural verifier.
3. Dialects:
   implement first-slice builtin, func, arith, SCF, affine, memref type, and
   vector type contracts behind native IntelliC module names.
4. Parser/printer:
   copy/adapt xDSL parsing and printing ideas into native modules, then prove
   canonical text round-trips for examples.
5. Surface construction:
   implement builder stack, `func.ir_function`, arith builders/operator hook,
   SCF region helpers, and affine map/set/op builders.
6. Semantics:
   implement `TraceDB`, typed schemas, semantic levels, registry resolution,
   region runner, concrete interpreter, and first-slice semantic definitions.
7. Actions and passes:
   implement the shared-pass-style actions named in the design, with mutation
   intents, mutator stage, and pending-record gate.
8. Evidence tests:
   prove `sum_to_n(5) -> 10`, affine access/legality facts, parser/printer
   round-trip, construction evidence, mutation evidence, and failure modes.

## Verification Criteria

- `python -m unittest discover -s tests` passes.
- Repo harness policy passes.
- `python -c "import intellic"` succeeds.
- Parser/printer round-trip tests preserve operation, region, block, value, type,
  and attribute structure for the first-slice examples.
- Structural verifier rejects broken parent links, missing terminators, type
  mismatches, stale uses, invalid `func.call`, malformed SCF regions, and affine
  dim/symbol/type mismatches.
- Surface construction builds the same structural IR as canonical text for the
  `sum_to_n` example.
- Concrete semantic execution records `TraceDB` evidence and computes
  `sum_to_n(5) -> 10`.
- Action tests show canonicalization, CSE, constant propagation, dead-code
  cleanup, single-call inlining, LICM, affine lowering/normalization, and
  pending-record-gate behavior with concrete mutation/evidence contracts.

## Tests

Initial verification for PR start:

```bash
python scripts/check_repo_harness.py
python -m unittest tests/test_repo_harness.py
```

Batch 1 verification:

```bash
python -c "import intellic; print(intellic.__version__)"
python -m unittest tests/test_imports.py
python scripts/check_repo_harness.py
python -m unittest discover -s tests
```

Batch 2 verification:

```bash
python -m unittest tests/test_syntax_core.py
python -m unittest discover -s tests
```

Batch 3 verification:

```bash
python -m unittest discover -s tests/dialects
python -m unittest discover -s tests
```

Batch 4 verification:

```bash
python -m unittest discover -s tests/parser
python -m unittest discover -s tests
```

Batch 5 verification:

```bash
python -m unittest tests/test_surface_builders.py
python -m unittest discover -s tests
```

Batch 6 verification:

```bash
python -m unittest tests/test_semantics.py
python -m unittest discover -s tests
```

Batch 7 verification:

```bash
python -m unittest discover -s tests/actions
python -m unittest discover -s tests
```

Batch 8 verification:

```bash
python -m unittest tests/test_examples.py
python -m unittest discover -s tests/parser
python -m unittest discover -s tests
python scripts/check_repo_harness.py
```

Final review missing-contract verification:

```bash
python -m unittest discover -s tests/dialects
# Ran 20 tests: OK

python -m unittest tests/test_semantics.py
# Ran 8 tests: OK

python -m unittest discover -s tests/actions
# Ran 62 tests: OK

python -m unittest discover -s tests/parser
# Ran 17 tests: OK

python -m unittest tests/test_examples.py
# Ran 2 tests: OK

python -m unittest discover -s tests
# Ran 129 tests: OK

python scripts/check_repo_harness.py
# repo harness policy passed

python -c "import intellic; print(intellic.__version__)"
# 0.1.0
```

Final review gaps closed:

- Full SCF syntax and verifier contracts are covered, including multi-region
  forms, terminator context validation, round-trip parsing/printing, and lazy
  dialect verifier bootstrap.
- Direct `func.call` concrete execution is covered through symbol lookup,
  argument/result validation, trace evidence, and recursion rejection.
- First-slice shared actions now have concrete behavior and evidence for CSE,
  symbol/dead-code cleanup, canonicalization, sparse constant propagation,
  single-call inlining, LICM, affine lowering/normalization, and action mutation
  safety/rollback.

Organization hardening verification:

```bash
python -m unittest tests.organization.test_public_layout
# Ran 2 tests: OK

python -m unittest tests.parser.test_golden_ir
# Ran 1 test: OK

python -m unittest discover -s tests
# Ran 132 tests: OK
```

Organization changes:

- Concrete dialect definitions live under `intellic/dialects/`; `intellic/ir/`
  keeps the common syntax/parser/semantics/action infrastructure.
- Concrete pass implementations live under `intellic/actions/`; common action
  records, stages, and pipeline infrastructure remain under `intellic/ir/actions/`.
- Large action, dialect, and parser/printer tests are split into focused
  subfolders under `tests/actions/`, `tests/dialects/`, and `tests/parser/`.
- Parser tests now include golden IR printing and `original ==
  print(parse(original))` idempotence assertions.

Final merge-review blocker verification:

```bash
python -m unittest tests.parser.test_golden_ir tests.parser.test_roundtrip tests.parser.test_diagnostics tests.parser.test_scf_verification
# Ran 18 tests: OK

python -m unittest tests.test_syntax_core
# Ran 9 tests: OK

python -m unittest tests.test_examples
# Ran 2 tests: OK

python -m unittest discover -s tests
# Ran 134 tests: OK

python scripts/check_repo_harness.py
# repo harness policy passed

python -c "import intellic; print(intellic.__version__)"
# 0.1.0
```

Final merge-review blockers closed:

- Canonical generic IR printing and parsing now use MLIR/xDSL-style property
  dictionaries and function types, not Python literal pseudo syntax.
- The structural verifier rejects stale or extra SSA use-list records.
- Non-empty zero-result `scf.if` regions must terminate with `scf.yield`.
- Challenging examples assert golden IR text and `original ==
  print(parse(original))` idempotence, including affine object properties.

Expected implementation test groups:

- `tests/test_syntax_core.py`
- `tests/dialects/`
- `tests/parser/`
- `tests/test_surface_builders.py`
- `tests/test_semantics.py`
- `tests/actions/`
- `tests/test_examples.py`

## Docs

- Keep accepted design docs stable unless implementation reveals a contract gap.
- Update this task as implementation milestones complete.
- Keep `docs/todo/README.md` aligned with the active implementation branch.

## Closeout

Before merge:

- Update `docs/todo/README.md` to mark completed implementation gaps.
- Remove this task file from `docs/in_progress/`.
- Archive `docs/in_progress/human_words/` under the PR archive folder.
- Ensure CI and local verification evidence are reflected in the PR body.
