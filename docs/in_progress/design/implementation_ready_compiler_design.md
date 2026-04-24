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
   named test class, fixture, or manual evidence artifact.
6. Deferred work: clear boundaries for declarative op definitions, full custom
   assembly, advanced eqsat, C++ ABI, and broad agent workflows.

## Examples

- Example: construct `arith.constant`, `arith.addi`, and `func.return` through
  Python builders.
- Feature shown: syntax object creation, active insertion point, use-list
  updates, construction evidence, and structural verification.
- Verification mapping: `tests/test_syntax_builder.py` with assertions for
  operation order, result ownership, operand uses, and expected failure when no
  insertion point exists.

- Example: register concrete and abstract semantics for `arith.addi`.
- Feature shown: typed operation owner, typed level keys, registry conflict
  checks, and TraceDB fact writes.
- Verification mapping: `tests/test_semantic_registry.py` and
  `tests/test_trace_db.py` with conflict and missing-fact cases.

- Example: run add-zero canonicalization as a `Fixed` compiler action.
- Feature shown: match records, mutation intents, mutator stage, and pending
  record gate.
- Verification mapping: `tests/test_actions.py` with successful replacement,
  rejected replacement, and pending-intent failure cases.

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
