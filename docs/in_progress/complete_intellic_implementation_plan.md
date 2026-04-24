# Complete IntelliC Implementation Plan

> For implementation workers: execute this plan task by task. Keep commits small
> and run the listed verification before moving to the next batch.

## Goal

Build the complete first executable IntelliC compiler slice promised by the
accepted design: native syntax objects, first-slice dialects, parser/printer,
surface builders, semantics, shared-pass-style actions, examples, and tests.

## Architecture

Implementation follows the accepted dependency order. `intellic.ir.syntax` is
the base and cannot import semantics, actions, or surfaces. Dialects depend on
syntax. Parser/printer depend on syntax and dialect registration. Surfaces build
syntax but do not own semantic meaning. Semantics depend on syntax and `TraceDB`.
Actions consume syntax and semantic facts and mutate syntax only through recorded
mutation intents.

## Tech Stack

- Python standard library only for the first slice.
- `unittest` for tests, matching the existing repository harness.
- Native IntelliC modules under `intellic/`; no public runtime wrapper around
  `.repositories/xdsl`.
- xDSL/MLIR local checkouts are reference inputs only.

## File Ownership Map

Create these files in the implementation batches below:

```text
pyproject.toml
intellic/__init__.py
intellic/ir/__init__.py
intellic/ir/syntax/__init__.py
intellic/ir/syntax/ids.py
intellic/ir/syntax/location.py
intellic/ir/syntax/type.py
intellic/ir/syntax/attribute.py
intellic/ir/syntax/value.py
intellic/ir/syntax/operation.py
intellic/ir/syntax/region.py
intellic/ir/syntax/builder.py
intellic/ir/syntax/verify.py
intellic/ir/syntax/context.py
intellic/ir/syntax/printer.py
intellic/ir/parser/__init__.py
intellic/ir/parser/lexer.py
intellic/ir/parser/parser.py
intellic/ir/dialects/__init__.py
intellic/ir/dialects/builtin.py
intellic/ir/dialects/func.py
intellic/ir/dialects/arith.py
intellic/ir/dialects/scf.py
intellic/ir/dialects/affine.py
intellic/ir/dialects/memref.py
intellic/ir/dialects/vector.py
intellic/surfaces/__init__.py
intellic/surfaces/api/__init__.py
intellic/surfaces/api/builders.py
intellic/surfaces/api/func.py
intellic/surfaces/api/arith.py
intellic/surfaces/api/scf.py
intellic/surfaces/api/affine.py
intellic/ir/semantics/__init__.py
intellic/ir/semantics/level.py
intellic/ir/semantics/schema.py
intellic/ir/semantics/trace_db.py
intellic/ir/semantics/semantic_def.py
intellic/ir/semantics/registry.py
intellic/ir/semantics/regions.py
intellic/ir/semantics/interpreter.py
intellic/ir/semantics/builtin.py
intellic/ir/actions/__init__.py
intellic/ir/actions/action.py
intellic/ir/actions/scope.py
intellic/ir/actions/match.py
intellic/ir/actions/mutation.py
intellic/ir/actions/stages.py
intellic/ir/actions/pipeline.py
intellic/ir/actions/host.py
intellic/ir/actions/passes.py
intellic/examples/__init__.py
intellic/examples/sum_to_n.py
intellic/examples/affine_tile.py
tests/test_imports.py
tests/test_syntax_core.py
tests/test_dialects.py
tests/test_parser_printer.py
tests/test_surface_builders.py
tests/test_semantics.py
tests/test_actions.py
tests/test_examples.py
```

## Batch 1: Package Foundation

**Files**

- Create: `pyproject.toml`
- Create: `intellic/__init__.py`
- Create: `intellic/ir/__init__.py`
- Create: `tests/test_imports.py`
- Modify: `docs/in_progress/complete_intellic_implementation.md`

**Implementation**

- Add minimal project metadata with package name `intellic`, Python
  requirement `>=3.10`, and no runtime dependencies.
- Export a package version string from `intellic/__init__.py`.
- Keep imports side-effect free.

**Verification**

```bash
python -c "import intellic; print(intellic.__version__)"
python -m unittest tests/test_imports.py
python scripts/check_repo_harness.py
python -m unittest discover -s tests
```

Expected result: all commands pass; import prints a non-empty version string.

**Commit**

```bash
git add pyproject.toml intellic tests/test_imports.py docs/in_progress/complete_intellic_implementation.md
git commit -m "feat: add intellic package foundation"
```

## Batch 2: Syntax Core

**Files**

- Create: `intellic/ir/syntax/ids.py`
- Create: `intellic/ir/syntax/location.py`
- Create: `intellic/ir/syntax/type.py`
- Create: `intellic/ir/syntax/attribute.py`
- Create: `intellic/ir/syntax/value.py`
- Create: `intellic/ir/syntax/operation.py`
- Create: `intellic/ir/syntax/region.py`
- Create: `intellic/ir/syntax/builder.py`
- Create: `intellic/ir/syntax/verify.py`
- Create: `intellic/ir/syntax/context.py`
- Create: `tests/test_syntax_core.py`

**Implementation**

- Implement stable identity objects for operations, values, blocks, and regions.
- Implement immutable `Type` and `Attribute` bases.
- Implement `Value`, `OpResult`, `BlockArgument`, and `Use`; operand changes
  must update old and new use lists.
- Implement `Operation.create(...)` for detached operations with results.
- Implement `Region` and `Block` ownership with parent links.
- Implement `Builder` and insertion points for controlled insertion.
- Implement structural verifier diagnostics for parent links, use lists, result
  types, region ownership, and terminators.
- Implement `Context` registration for dialect operations/types/attributes.

**Verification**

```bash
python -m unittest tests/test_syntax_core.py
python -m unittest discover -s tests
```

Expected result: tests cover detached operation creation, insertion, reparenting
failure, operand replacement use-list updates, block arguments, and verifier
failure messages.

**Commit**

```bash
git add intellic/ir/syntax tests/test_syntax_core.py docs/in_progress/complete_intellic_implementation.md
git commit -m "feat: implement syntax core"
```

## Batch 3: First-Slice Dialects

**Files**

- Create: `intellic/ir/dialects/builtin.py`
- Create: `intellic/ir/dialects/func.py`
- Create: `intellic/ir/dialects/arith.py`
- Create: `intellic/ir/dialects/scf.py`
- Create: `intellic/ir/dialects/affine.py`
- Create: `intellic/ir/dialects/memref.py`
- Create: `intellic/ir/dialects/vector.py`
- Create: `tests/test_dialects.py`

**Implementation**

- Implement builtin module operation and builtin scalar/index types.
- Implement `func.func`, `func.call`, and `func.return` with symbol/function
  type verification.
- Implement `arith.constant`, `arith.addi`, and `arith.index_cast`.
- Implement SCF operation classes and verification contracts for the full SCF
  family, with builder support required first for `scf.for` and `scf.yield`.
- Implement affine expression/map/set classes plus first operation classes:
  `affine.apply`, `affine.for`, `affine.if`, `affine.load`, `affine.store`,
  `affine.min`, and `affine.max`.
- Implement narrow `MemRefType` and `VectorType` type substrates.

**Verification**

```bash
python -m unittest tests/test_dialects.py
python -m unittest discover -s tests
```

Expected result: tests cover valid builders plus failures for invalid
`func.call`, malformed SCF regions, affine dim/symbol mismatch, invalid affine
step, memref rank mismatch, and vector element mismatch.

**Commit**

```bash
git add intellic/ir/dialects tests/test_dialects.py docs/in_progress/complete_intellic_implementation.md
git commit -m "feat: implement first-slice dialect contracts"
```

## Batch 4: Parser And Printer

**Files**

- Create: `intellic/ir/parser/lexer.py`
- Create: `intellic/ir/parser/parser.py`
- Extend: `intellic/ir/syntax/printer.py`
- Create: `tests/test_parser_printer.py`

**Implementation**

- Implement enough MLIR/xDSL-style lexing for identifiers, symbols, SSA values,
  block labels, integer literals, string literals, punctuation, types, and
  affine map/set syntax used by first-slice examples.
- Parse selected custom forms for builtin, func, arith, SCF, and affine examples.
- Parse generic operation form for registered operations.
- Print canonical text with deterministic SSA/block naming.
- Round-trip parser output through printer and parser again.

**Verification**

```bash
python -m unittest tests/test_parser_printer.py
python -m unittest discover -s tests
```

Expected result: tests round-trip `sum_to_n` and affine tiled access examples,
reject unknown custom ops, reject malformed regions, and preserve operation
identity structure across round-trip.

**Commit**

```bash
git add intellic/ir/parser intellic/ir/syntax/printer.py tests/test_parser_printer.py docs/in_progress/complete_intellic_implementation.md
git commit -m "feat: add canonical parser printer roundtrip"
```

## Batch 5: Python Surface Builders

**Files**

- Create: `intellic/surfaces/api/builders.py`
- Create: `intellic/surfaces/api/func.py`
- Create: `intellic/surfaces/api/arith.py`
- Create: `intellic/surfaces/api/scf.py`
- Create: `intellic/surfaces/api/affine.py`
- Create: `tests/test_surface_builders.py`

**Implementation**

- Implement active builder stack and construction evidence records.
- Implement `func.ir_function` for annotated function arguments and return
  conversion to `func.return`.
- Implement arith builder functions and optional `Value.__add__` policy.
- Implement `scf.for_` region helper for loop-carried examples.
- Implement affine expression/map/set helpers and operation builders.
- Reject host Python boolean use of symbolic values.

**Verification**

```bash
python -m unittest tests/test_surface_builders.py
python -m unittest discover -s tests
```

Expected result: tests build `sum_to_n` through Python APIs, compare the
structural IR against parsed canonical text, verify construction evidence, and
exercise builder failure paths.

**Commit**

```bash
git add intellic/surfaces tests/test_surface_builders.py docs/in_progress/complete_intellic_implementation.md
git commit -m "feat: add python surface builders"
```

## Batch 6: Semantics And TraceDB

**Files**

- Create: `intellic/ir/semantics/level.py`
- Create: `intellic/ir/semantics/schema.py`
- Create: `intellic/ir/semantics/trace_db.py`
- Create: `intellic/ir/semantics/semantic_def.py`
- Create: `intellic/ir/semantics/registry.py`
- Create: `intellic/ir/semantics/regions.py`
- Create: `intellic/ir/semantics/interpreter.py`
- Create: `intellic/ir/semantics/builtin.py`
- Create: `tests/test_semantics.py`

**Implementation**

- Implement `TraceRecord`, relation schemas, current/history projections,
  retraction, supersession, and typed require/query APIs.
- Implement semantic level keys and selection.
- Implement `SemanticDef` with typed owner keys and read/write declarations.
- Implement registry conflict detection and explicit resolution policies.
- Implement region runner and concrete interpreter dispatch.
- Implement concrete semantic definitions for constants, addi, index_cast,
  func.call, func.return, scf.for, scf.yield, affine map evaluation, affine
  access facts, and memory effects.

**Verification**

```bash
python -m unittest tests/test_semantics.py
python -m unittest discover -s tests
```

Expected result: tests compute `sum_to_n(5) -> 10`, record loop iterations,
record affine access facts, reject missing facts, reject registry conflicts, and
prove current/history projection behavior.

**Commit**

```bash
git add intellic/ir/semantics tests/test_semantics.py docs/in_progress/complete_intellic_implementation.md
git commit -m "feat: implement trace semantics"
```

## Batch 7: Actions And Shared Passes

**Files**

- Create: `intellic/ir/actions/action.py`
- Create: `intellic/ir/actions/scope.py`
- Create: `intellic/ir/actions/match.py`
- Create: `intellic/ir/actions/mutation.py`
- Create: `intellic/ir/actions/stages.py`
- Create: `intellic/ir/actions/pipeline.py`
- Create: `intellic/ir/actions/host.py`
- Create: `intellic/ir/actions/passes.py`
- Create: `tests/test_actions.py`

**Implementation**

- Implement `CompilerAction`, fixed-action host, action frames, and pipeline
  transactions.
- Implement `MatchRecord`, `MutationIntent`, `MutationApplied`, and
  `RewriteEvidence`.
- Implement `MutatorStage` as the only public syntax mutator.
- Implement `PendingRecordGate`.
- Implement first-slice actions: `verify-structure`, `canonicalize-greedy`,
  `common-subexpression-elimination`, `sparse-constant-propagation`,
  `symbol-dce-and-dead-code`, `inline-single-call`,
  `loop-invariant-code-motion`, `lower-affine-to-scf`,
  `normalize-and-simplify-affine-loops`.

**Verification**

```bash
python -m unittest tests/test_actions.py
python -m unittest discover -s tests
```

Expected result: tests show action records, no direct mutation in `apply`,
mutation application through `MutatorStage`, pending-record failure, add-zero
canonicalization, duplicate expression CSE, constant propagation, dead-code
erase, single-call inline, LICM movement, affine lowering evidence, and stale
legality rejection.

**Commit**

```bash
git add intellic/ir/actions tests/test_actions.py docs/in_progress/complete_intellic_implementation.md
git commit -m "feat: implement compiler actions"
```

## Batch 8: Examples, End-To-End Evidence, And Closeout

**Files**

- Create: `intellic/examples/sum_to_n.py`
- Create: `intellic/examples/affine_tile.py`
- Create: `tests/test_examples.py`
- Modify: `docs/in_progress/complete_intellic_implementation.md`
- Modify: `docs/todo/README.md`
- Modify: PR body

**Implementation**

- Provide reusable example builders for `sum_to_n` and affine tiled access.
- Add end-to-end tests that construct, print, parse, verify, execute, and run
  the first-slice action pipeline.
- Update task checklist with completed batches and exact verification evidence.

**Verification**

```bash
python -m unittest discover -s tests
python scripts/check_repo_harness.py
python -c "import intellic; print(intellic.__version__)"
```

Expected result: full test suite and repo policy pass; import succeeds.

**Commit**

```bash
git add intellic/examples tests/test_examples.py docs/in_progress/complete_intellic_implementation.md docs/todo/README.md
git commit -m "test: add end-to-end intellic examples"
```

## First Code Slice Boundary

Start implementation with Batch 1 only. Do not create syntax/dialect files until
the package imports, repo harness, and baseline test discovery all pass. Batch 1
is the first review checkpoint.

## Self-Review

- Spec coverage: all first-slice contracts from framework, syntax, semantics,
  and passes docs map to one of the eight batches.
- Placeholder scan: no planned batch depends on an unnamed file, unnamed command,
  or unspecified verification step.
- Type consistency: names match the accepted design module names and selected
  pass/action names.
- Scope control: backend lowering, full bufferization, production optimizer
  quality, declarative op definitions, and target-specific vector lowering stay
  outside this PR unless required to satisfy the listed first-slice evidence.
