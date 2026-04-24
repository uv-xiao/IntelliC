# Design: Compiler Framework

> Status: Accepted architecture design for IntelliC's compiler framework.

## Goal

IntelliC is an intelligent compiler infrastructure for both human programmers and
LLM agents. Its compiler core must be strong enough to support future compiler
construction above it: new programming surfaces, new IR levels, new dialects,
new semantic domains, new analyses, new transforms, new backends, and
agent-readable evidence.

The framework starts from these concepts:

```text
Lang := Surface | IR
Surface := IR + Construction API
IR := Sy + Se
```

`Lang` is a classification term. Most code and docs should talk directly about
`Surface` or `IR` because they have different contracts.

## Decision

Pick **C. MLIR/xDSL-Derived Syntax Plus First-Class IntelliC Semantics**.

IntelliC will define a Python-native compiler infrastructure whose IR syntax strictly
matches MLIR/xDSL textual structure, while semantics, analysis, transform, and
pipeline mechanisms are designed as first-class IntelliC contracts. This is the
durable direction for the clean branch.

The selected split is:

- `Sy`: syntax, structure, identity, verification, canonical MLIR/xDSL-style
  text, and IR parsing.
- `Se`: thin level-keyed semantic definitions over syntax, expressed through
  transitions over a shared semantic state/fact/event database.
- Surface construction APIs: Python-native builders, decorators, operator
  hooks, and region helpers that construct IR without parser-level composition.
- Pipeline infrastructure: a unified action mechanism for IR parsing, analysis,
  rewriting, semantic execution, gates, LLM-agent steps, and backend handoff.

## Surface Construction And IR Parsing

IntelliC should not make Pythonic authoring depend on a hardened or composable
surface parser. Parser-level composition is too complex for the first clean
architecture. The human/LLM-facing surface should instead be a Python
construction API over IR.

```text
surface_api:
  Python builders and decorators for human/LLM-facing programming surfaces
  each builder constructs native Sy objects or canonical IR fragments
  shares insertion context, diagnostics, symbol binding, type helpers, evidence,
  and round-trip hooks

ir_parser:
  strict MLIR/xDSL-style parser for canonical IR text
  based on xDSL's existing Python parser, copied into native IntelliC and adjusted
  only where IntelliC architecture requires it
```

Surface APIs should be modular but they compose as Python construction
primitives, not grammar or AST parser extensions. Dialects and operations may
provide builder functions, type constructors, operator hooks, decorators, and
region/context-manager helpers. A final decorator can stage a Python function by
creating symbolic IR values, executing the function under an insertion context,
collecting emitted operations, and verifying the resulting `Sy` graph.

The IR parser has a different contract: it must parse the canonical IR syntax
accepted by MLIR/xDSL, including generic and custom operation forms. It is not
responsible for accepting Pythonic syntax.

## Design Decomposition

This umbrella document records the architectural choice and links the concrete
subdesigns:

- `docs/design/compiler_syntax.md` — `Sy`, copied/adapted from
  xDSL classes where useful, with strict MLIR/xDSL syntax format, Python-native
  surface construction APIs, and a separate strict `ir_parser` contract.
- `docs/design/compiler_semantics.md` — `Se`, designed as thin
  `SemanticDef` records bound to typed owners and extensible semantic level keys
  over a shared `TraceDB`, rather than a single semantic definition per
  operation.
- `docs/design/compiler_passes.md` — unified compiler actions for
  analysis, rewrite, pass, gate, semantic execution, LLM-agent participation,
  and backend handoff.

The child docs own detailed contracts. This file should not duplicate those
contracts beyond the cross-cutting requirements below.

## Framework Shape

Planned package ownership:

```text
intellic/
  ir/
    syntax/          # copied/adapted xDSL-style Operation, Region, Block, etc.
    semantics/       # SemanticDef records, transition relations, TraceDB
    actions/         # unified analysis/rewrite/pass/gate/action execution
    dialects/        # dialect registration and extension ownership
    parser/          # ir_parser: strict canonical IR parser
  surfaces/
    api/             # decorators, builders, insertion contexts, evidence
  examples/          # small executable examples used as evidence
```

Core dependency direction:

```text
surface_api decorators/builders
      |
      v
  Sy objects  <---- dialect definitions
      | \
      |  \-> canonical IR text <----> ir_parser
      v
  Se definitions and TraceDB updates
      |
      v
Unified compiler actions
      |
      v
Evidence: source maps, TraceDB, e-graphs, artifacts, review notes
```

`Sy` owns structural shape and MLIR/xDSL-compatible syntax. `Se` depends on
`Sy`, but it must not be hidden inside parser or action-local metadata. Compiler
actions depend on both `Sy` and `Se` and record semantic changes in `TraceDB`.

## Cross-Cutting Contracts

- Every canonical IR program is `IR := Sy + Se`, not syntax alone.
- `surface_api` and `ir_parser` are different layers. `surface_api` constructs
  IR through Python builders and decorators; `ir_parser` reads canonical IR
  text.
- `ir_parser` must strictly match MLIR/xDSL canonical syntax.
- Pythonic surface authoring must not require AST/parser-level composition.
- Native IntelliC syntax classes are copied/adapted from xDSL where useful; they are
  not imported through wrappers as IntelliC's public architecture.
- IntelliC is the infrastructure name, not a dialect name. Examples should use
  MLIR-style dialect names such as `builtin`, `func`, and `arith`, or future
  real project dialect names once designed.
- A single operation may have multiple level-specific `SemanticDef` records.
  Level keys are extensible; examples include concrete value, abstract range,
  symbols, or backend evidence semantics.
- Equality saturation/e-graph reasoning should be modeled as explicit IR
  operations plus compiler actions, not as a `SemanticDef` level.
- Effects, obligations, diagnostics, and pass gates should be represented as
  typed `TraceDB` event/fact relations or projections unless a later design
  proves a more specific abstraction is necessary.
- Compiler pipeline pieces should share one action mechanism where possible;
  analysis, rewrite, pass, gate, semantic execution, and LLM-agent participation
  are specializations of action execution rather than unrelated subsystems.
- Compiler actions are classified as `Fixed` or `AgentAct`. `AgentEvolve` is a
  separate JIT-like workflow that generates verified `Fixed` actions.
  Actions record matches, facts, evidence, and mutation intents in `TraceDB`;
  syntax mutation is performed by explicit mutator stages that consume those
  records.
- A compiler pipeline has one authoritative `TraceDB` per run, with action
  frames, transactions, checkpoints, and optional speculative overlays for
  agent work.
- Actions may also create auxiliary `TraceDB` instances for local computation,
  but only records exported into the pipeline `TraceDB` participate in shared
  pipeline logic, gates, replay, or cross-action reuse.
- Fast shared pipeline lookup stays inside the authoritative `TraceDB` through
  declared relation indexes and optional materialized projections rather than a
  separate pipeline-level analysis-cache subsystem.
- Python and future C++ actions should share one language-neutral action host
  contract and canonical `TraceDB`/evidence schemas.
- Every design example maps to evidence before implementation starts. For
  documentation-only work, evidence may be a focused reread, link/path check,
  or policy check rather than automated tests.

## Implementation-Ready Build Order

The first executable compiler slice should be built in dependency order. Later
layers may define interfaces early, but they must not force lower layers to
depend on higher-level conveniences.

1. `intellic.ir.syntax`: identity objects, parent links, use lists, regions,
   blocks, operation creation, structural verification, and mutation APIs.
2. `intellic.ir.dialects`: `builtin`, `func`, `arith`, and the minimal `scf`
   syntax definitions needed for a loop-carried region example.
3. `intellic.ir.parser` and printer: canonical MLIR/xDSL-compatible text for
   the selected operation forms, with round-trip evidence.
4. `intellic.surfaces.api`: builder stack, insertion points, named dialect
   builders, `func.ir_function`, optional `Value.__add__`, and construction
   evidence over `Sy`.
5. `intellic.ir.semantics`: minimal `TraceDB`, typed relation schemas, semantic
   level keys, typed owner registration, registry resolution, and generated
   concrete interpreter for straight-line and loop-carried region examples.
6. `intellic.ir.actions`: `Fixed` action host, match records, mutation intents,
   mutator stage, pending-record gate, and one pipeline `TraceDB`.

The build order is also the dependency rule: syntax must not import semantics,
actions, or surfaces; semantics may import syntax and `TraceDB`; actions may
import syntax and semantics; surfaces may import syntax and dialect builders but
must not own semantic meaning.

## First Implementation Slice Contract

The first slice is complete only when one challenging program crosses the
planned layers with evidence. Tiny straight-line functions are useful local
smoke tests, but they are too easy to prove the architecture. The
implementation-ready proof point is a loop-carried `sum_to_n` example:

```python
@func.ir_function
def sum_to_n(n: index) -> i32:
    zero_i = arith.constant(0, index)
    one_i = arith.constant(1, index)
    zero = arith.constant(0, i32)

    with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
        i, total = loop.arguments
        total_next = arith.addi(total, arith.index_cast(i, i32))
        scf.yield_(total_next)

    return loop.results[0]
```

Required evidence:

- Python builders create native `Sy` objects for `builtin.module`, `func.func`,
  `arith.constant`, `arith.addi`, `arith.index_cast`, `scf.for`, `scf.yield`,
  and `func.return`.
- The printer emits canonical MLIR/xDSL-compatible text, and the strict parser
  round-trips that text into an equivalent object graph.
- Structural verification checks parent links, region/block ownership, result
  types, block arguments, loop-carried argument/result pairing, terminators, and
  use lists.
- Concrete semantic execution records `ValueConcrete`, `Evaluated`, and
  `RegionResult` facts/events in `TraceDB` and computes `sum_to_n(5) -> 10`.
- A `Fixed` action records at least one loop-body canonicalization match, such
  as replacing `addi(total, 0)` if present in a variant fixture, writes a
  mutation intent, applies it through `MutatorStage`, and fails if required
  pending records remain unhandled.

The first slice does not need broad dialect coverage. It needs enough depth for
the object model, semantics model, and action model to prove their contracts.

## Examples

### Example 1: One Feature Crosses All Subsystems

Surface:

```python
@func.ir_function
def sum_to_n(n: index) -> i32:
    zero_i = arith.constant(0, index)
    one_i = arith.constant(1, index)
    zero = arith.constant(0, i32)

    with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
        i, total = loop.arguments
        total_next = arith.addi(total, arith.index_cast(i, i32))
        scf.yield_(total_next)

    return loop.results[0]
```

Canonical IR sketch:

```mlir
"builtin.module"() ({
  func.func @sum_to_n(%n: index) -> i32 {
    %c0_i = arith.constant 0 : index
    %c1_i = arith.constant 1 : index
    %c0 = arith.constant 0 : i32
    %sum = scf.for %i = %c0_i to %n step %c1_i
        iter_args(%total = %c0) -> (i32) {
      %i32 = arith.index_cast %i : index to i32
      %next = arith.addi %total, %i32 : i32
      scf.yield %next : i32
    }
    func.return %sum : i32
  }
}) : () -> ()
```

Decomposition:

```text
surface_api:
  create symbolic function arguments
  execute the Python function under an insertion context
  build scf.for with nested body region and loop-carried values
  lower index_cast/addi/yield/return through registered builders
  produce Sy objects plus builder-call and region-construction evidence

ir_parser:
  parse strict MLIR/xDSL-style canonical text when reading or round-tripping IR

compiler_syntax.md:
  define copied/adapted Operation, Region, Block, Value, Type, Attribute classes
  and high-level Python construction APIs

compiler_semantics.md:
  attach level-keyed SemanticDef records to builtin/func/arith/scf operations
  execute child regions through TraceDB-backed region conventions

compiler_passes.md:
  run unified actions for interpretation, loop-body rewriting, eqsat, gates,
  and review
```

Verification mapping: construction API example evidence, nested-region
round-trip evidence, semantic database evidence for `sum_to_n(5) -> 10`, and
action-pipeline evidence for loop-body canonicalization.

### Example 2: E-Graph Reasoning Is A Mechanism, Not Per-Op Equivalence Fields

Rewrite family:

```text
arith.addi(%x, %zero) <=> %x
arith.muli(%x, %one)  <=> %x
```

Feature shown: equivalence belongs in an equality-saturation/e-graph mechanism
modeled with IR operations and actions that can consume rewrite rules and cost
models. Operation semantics do not need per-op equivalence fields.

Verification mapping: e-graph action evidence records e-class creation,
saturation rules, extraction cost, and chosen replacement.

## Acceptance Criteria

- `compiler_framework.md` records only the selected architectural decision,
  surface construction boundary, strict IR parser boundary, decomposition, and
  cross-cutting requirements.
- Syntax, semantics, and pass mechanisms each have focused design drafts.
- The syntax design avoids declarative operation-definition machinery as an
  initial dependency, distinguishes Python-native surface construction from
  strict `ir_parser`, and commits to strict MLIR/xDSL syntax.
- The semantics design defines how IRs, dialects, regions, and operations
  contribute thin level-keyed `SemanticDef` records, and treats
  effects/obligations/diagnostics as `TraceDB` projections until proven
  otherwise.
- The framework keeps eqsat/e-graph reasoning out of `SemanticDef` levels and
  represents it through operation-modeled IR plus actions.
- The passes design unifies pass, analysis, rewrite, gates, semantic execution,
  and LLM-agent pipeline participation around one action mechanism with `Fixed`
  and `AgentAct` action kinds, a separate `AgentEvolve` fixed-action generation
  workflow, mutator stages for syntax changes, `TraceDB`-native indexing, and a
  shared cross-language action/evidence contract.

## Out Of Scope

- Direct implementation of the compiler core.
- Designing a complete surface language.
- Parser-level composition for Pythonic source surfaces.
- Backend lowering details beyond semantic/evidence boundaries.
- Treating `intellic` as a dialect name before dialect design exists.

## Closeout

When implemented, promote the umbrella and child designs into `docs/design/`,
update `docs/todo/README.md`, and remove completed in-progress drafts.
