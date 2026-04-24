# Design: Implementation-Ready Compiler Design

## Goal

Turn IntelliC's accepted compiler architecture into an implementation-ready
design for the first executable compiler slice.

Implementation-ready means the docs name concrete module ownership, public
contracts, dependency order, invariants, failure modes, examples, and
verification evidence. The goal is not to implement the compiler in this PR; it
is to remove ambiguity that would otherwise block or distort implementation.

## Context

The accepted architecture already defines:

- `IR := Sy + Se`
- Python-native surface construction APIs, separate from strict canonical
  `ir_parser`
- xDSL/MLIR-derived syntax objects copied/adapted behind native IntelliC APIs
- thin typed `SemanticDef` records over `TraceDB`
- unified compiler actions with `Fixed`, `AgentAct`, and separate `AgentEvolve`

The remaining gap is implementation readiness. The current docs describe the
shape, but the next PR needs more exact boundaries: what to build first, how
objects interact, which records are minimal, and which examples become tests.

## Alternatives

### A. Keep Accepted Architecture As-Is

This avoids churn, but it leaves too much design interpretation to the
implementation PR. The first implementation slice would need to decide module
boundaries, ordering, and verification while also writing code.

### B. Write A Separate Implementation Plan Only

This gives sequencing, but implementation plans tend to duplicate design
contracts without updating the accepted architecture. The project would then
have two sources of truth.

### C. Refine Accepted Design With An In-Progress Staging Draft

Use this draft to work out the implementation-ready details, then promote the
stable parts into the accepted `docs/design/compiler_*.md` files before merge.
This keeps the accepted docs as the source of truth while preserving review
space during the PR.

## Selected Design

Use alternative C.

This PR will produce implementation-ready accepted docs by clarifying six
surfaces:

1. Build order: syntax core, parser/printer shape, TraceDB, semantic registry,
   action host, surface builders.
2. Module ownership: planned packages, file groups, public contracts, and
   dependency direction.
3. First-slice APIs: exact minimal constructors, mutation APIs, TraceDB record
   APIs, semantic registration APIs, action execution APIs, and surface builder
   APIs.
4. Invariants and failure modes: parent/use-list integrity, typed registration,
   transaction boundaries, pending mutation intents, symbolic Python control
   flow rejection, and strict parser rejection.
5. Example-to-test mapping: every example in the accepted design maps to a
   named test class, fixture, or manual evidence artifact. Primary examples must
   be challenging enough to force nested regions, loop-carried values, TraceDB
   facts, and action-driven mutation to cooperate.
6. Deferred work: clear boundaries for declarative op definitions, full custom
   assembly, advanced eqsat, C++ ABI, and broad agent workflows.

This PR also makes two dialect requirements explicit:

- `scf` is full-dialect scope. The implementation design must cover `if`,
  `for`, `while`, `execute_region`, `index_switch`, `parallel`, `reduce`,
  `reduce.return`, `condition`, `yield`, `forall`, and `forall.in_parallel`,
  even if implementation lands in batches.
- `affine` is a first-class optimization dialect. The design must cover affine
  expressions, maps, sets, affine loops/conditionals/parallelism, affine memory
  access, affine min/max/apply, DMA/prefetch/index transforms, and legality
  evidence for transformations.
- Affine memory operations need a first-slice type substrate for `MemRefType`
  and `VectorType`, but broad memref/vector dialect behavior remains deferred.
  The accepted syntax design now names the narrow type contracts needed for
  affine load/store/vector_load/vector_store verification.
- `scf.forall` must be modeled with explicit iteration, shared-output, merge,
  and synchronization evidence. It cannot be treated as a sequential loop whose
  replay order accidentally proves parallel legality.

## Examples

- Example: construct `sum_to_n` with `scf.for_`, loop-carried `iter_args`,
  `arith.index_cast`, `arith.addi`, `scf.yield_`, and `func.return_` through
  Python builders.
- Feature shown: syntax object creation, nested region ownership, active
  insertion points, block arguments, use-list updates, loop result ownership,
  construction evidence, and structural verification.
- Verification mapping: `tests/test_syntax_builder.py` with assertions for
  operation order, nested region/block parentage, loop-carried
  argument/result/yield counts, result ownership, operand uses, and expected
  failure when no insertion point exists.

- Example: register concrete semantics for `arith.constant`, `arith.index_cast`,
  `arith.addi`, `scf.for`, `scf.yield`, and `func.return`.
- Feature shown: typed operation owner, typed level keys, registry conflict
  checks, TraceDB fact writes, child-region execution, and loop-carried value
  updates.
- Verification mapping: `tests/test_semantic_registry.py` and
  `tests/test_trace_db.py` with `sum_to_n(5) -> 10`, conflict,
  missing-fact, bad step, and mismatched-yield cases.

- Example: run add-zero canonicalization inside the `scf.for` body as a `Fixed`
  compiler action.
- Feature shown: nested-region match records, mutation intents, mutator stage,
  use-list preservation, loop-yield preservation, and pending record gate.
- Verification mapping: `tests/test_actions.py` with successful replacement,
  rejected replacement, and pending-intent failure cases.

- Example: parse and verify an affine tiled loop nest with `affine.for`,
  `affine.apply`, `affine.load`, `affine.store`, and affine map symbols.
- Feature shown: dimension/symbol distinction, affine bound verification,
  memory-access fact extraction, and legality-gated action prerequisites.
- Verification mapping: `tests/test_affine_syntax.py`,
  `tests/test_affine_semantics.py`, and `tests/test_affine_actions.py` with
  invalid symbol-use, map-operand mismatch, and dependence-legality cases.

## First-Slice Pass Set

The first executable slice should implement important shared MLIR/xDSL-style
passes before bespoke IntelliC-only optimization examples:

1. `verify-structure`
2. `canonicalize-greedy`
3. `common-subexpression-elimination`
4. `sparse-constant-propagation`
5. `symbol-dce-and-dead-code`
6. `inline-single-call`
7. `loop-invariant-code-motion`
8. `lower-affine-to-scf`
9. `normalize-and-simplify-affine-loops`
10. `pending-record-gate`

This set is still implementation-sized, but it follows upstream priorities:
canonicalization, CSE, constant propagation, symbol/dead-code cleanup, inlining,
LICM, and affine lowering/normalization are shared compiler infrastructure in
MLIR and xDSL. The slice must cover builtin, func, arith, scf, affine, minimal
memref types, and minimal vector types through these passes. `sum_to_n` remains
semantic verification evidence, and add-zero folding becomes a canonicalizer test
case instead of its own pass.

## Contracts

- Accepted design docs remain the final source of truth after this PR closes.
- `docs/in_progress/design/implementation_ready_compiler_design.md` is a staging
  draft and must be removed or promoted before merge.
- No compiler implementation code is added in this PR unless needed for a docs
  policy check.
- The next implementation PR must be able to derive its module plan and first
  test list directly from the accepted docs.

## Verification

Documentation-only verification:

```bash
python scripts/check_repo_harness.py
python -m unittest tests/test_repo_harness.py
```

Focused review evidence:

- reread changed accepted design sections
- check all referenced paths exist or are explicitly future paths
- verify `docs/todo/README.md`, `docs/in_progress/README.md`, and this task
  agree about active work

## Closeout

Before merge:

- promote stable implementation-ready details into `docs/design/compiler_*.md`
- update `docs/todo/README.md`
- remove this staging draft if its content has been promoted
- keep `docs/in_progress/implementation_ready_compiler_design.md` updated until
  the PR is closed
