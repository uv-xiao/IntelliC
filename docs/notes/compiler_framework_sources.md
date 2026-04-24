# Compiler Framework Source Reading Report

- **Date**: 2026-04-20
- **Purpose**: Ground the clean IntelliC compiler framework design in MLIR, xDSL,
  and the previous `origin/htp/v0` architecture without importing legacy
  implementation shape.

## Sources

- `.repositories/llvm-project` at `f2efeabe3`
- `.repositories/xdsl` at `d875f35`
- `.references/acm-3729331.pdf` downloaded from the author-hosted PDF for DOI
  `10.1145/3729331` after the ACM PDF endpoint returned HTTP 403
- `.repositories/egg` at `f94c346`
- `.repositories/egglog` at `b27cd22`
- `origin/htp/v0`
- `docs/story.md`
- `docs/design/agent_harness.md`

## Source Scope Map

| Source | Scope Read | Useful Shape | IntelliC Use |
| --- | --- | --- | --- |
| MLIR LangRef | Operations, blocks, regions, dialects, attributes, types | Uniform extensible IR syntax | `Sy` object model |
| MLIR operation definitions | ODS, traits, operands, results, verification | Single operation record as source of truth | `OpDef` syntax and verifier contract |
| MLIR attributes/types docs | Open type system, immutable value-typed attributes/types | Explicit compile-time data and value typing | `Type` and `Attribute` contracts |
| xDSL IR core | Python `Operation`, `Region`, `Block`, `Attribute` classes | Python-native MLIR-style syntax | IntelliC Python-native IR objects |
| xDSL parser/printer | MLIR-compatible generic/custom operation syntax | Existing Python `ir_parser` shape | Native IntelliC `ir_parser` copied/adapted from xDSL |
| xDSL interpreter | Operation implementation dispatch and execution trace hooks | Executable operation behavior | `Se` semantics functions |
| xDSL SCF dialect/interpreter | `scf.if`, `scf.for`, `scf.while`, `scf.execute_region`, `scf.index_switch`, `scf.parallel`, reductions, yields, and condition scheduling examples | Control operations run child regions through the interpreter | Operation-owned control semantics with region runner support |
| MLIR SCF operation definitions | Full `scf` dialect, including `scf.forall` and `scf.forall.in_parallel` beyond the current xDSL subset | Full structured-control-flow operation contracts | IntelliC full-SCF syntax/semantics/action coverage |
| xDSL affine dialect and affine IR | `AffineExpr`, `AffineMap`, `AffineSet`, `affine.apply`, `affine.for`, `affine.if`, `affine.parallel`, load/store, min, yield | Python-native affine syntax and verifier patterns | IntelliC affine syntax and first semantic/action contracts |
| MLIR affine operation definitions | Full affine operation family: maps/sets, apply/min/max, loops, memory, prefetch, DMA, index transforms | Complete affine dialect contract | IntelliC affine design source of truth where xDSL lacks operations |
| xDSL eqsat docs/transforms | E-class insertion, PDL-interp eqsat rewrites, costs, extraction | E-graph pipeline embedded in IR | Equality reasoning as operation-modeled IR plus actions |
| Fjfj PLDI 2025 paper | Rule/method semantics, partial transition relations, modular verification | Trace-updating semantics with restrictions | `Se` trace model and modular semantic domains |
| egg | E-graphs, rewrites, analyses, cost functions, extraction, explanations | Equality saturation core ideas | Possible backend for equivalence actions |
| egglog | Datalog-style equality saturation, relations, schedules, extraction | Relational/action-oriented saturation | Possible backend for TraceDB/e-graph actions |
| `origin/htp/v0` docs/code | Python surfaces, replay, typed semantic state | Human/agent-friendly artifacts | Surface and evidence requirements |

## xDSL Syntax Reference Map

The syntax draft now links directly to the local xDSL and MLIR sources that
cover most of the planned `Sy` implementation:

| IntelliC Syntax Concern | Local Reference |
| --- | --- |
| Operation, region, block, SSA value, use, dialect, attribute, and type objects | `.repositories/xdsl/xdsl/ir/core.py` |
| Dialect/context registration | `.repositories/xdsl/xdsl/context.py` |
| MLIR-compatible parsing and SSA/block reference handling | `.repositories/xdsl/xdsl/parser/core.py`, `.repositories/xdsl/xdsl/utils/mlir_lexer.py` |
| Printing and SSA/block name allocation | `.repositories/xdsl/xdsl/printer.py` |
| Insertion points and mutation discipline | `.repositories/xdsl/xdsl/rewriter.py`, `.repositories/xdsl/docs/marimo/builders.py` |
| Human-readable MLIR/xDSL syntax examples | `.repositories/xdsl/docs/marimo/mlir_ir.py`, `.repositories/xdsl/docs/marimo/xdsl_introduction.py` |
| First-slice dialect examples | `.repositories/xdsl/xdsl/dialects/builtin.py`, `.repositories/xdsl/xdsl/dialects/func.py`, `.repositories/xdsl/xdsl/dialects/arith.py`, `.repositories/xdsl/xdsl/dialects/cf.py`, `.repositories/xdsl/xdsl/dialects/scf.py`, `.repositories/xdsl/xdsl/dialects/affine.py`, `.repositories/xdsl/xdsl/dialects/memref.py`, `.repositories/xdsl/xdsl/dialects/vector.py` |
| Full SCF operation contract | `.repositories/llvm-project/mlir/include/mlir/Dialect/SCF/IR/SCFOps.td` |
| Full affine operation contract | `.repositories/llvm-project/mlir/include/mlir/Dialect/Affine/IR/AffineOps.td`, `.repositories/llvm-project/mlir/docs/Dialects/Affine.md` |
| MLIR textual and operation-definition background | `.repositories/llvm-project/mlir/docs/LangRef.md`, `.repositories/llvm-project/mlir/docs/DefiningDialects/Operations.md` |

The local reference checkout is evidence for design and implementation. It must
not become a public runtime wrapper dependency for IntelliC.

## Visual Model

```text
Lang
  |
  +--> Surface
  |      |
  |      `--> Parser
  |             |
  |             v
  |            IR
  |
  `--> IR
         |
         +--> Sy  syntax: Operation, Region, Block, Type, Attribute
         `--> Se  semantics: run behavior, effects, obligations, evidence
```

## Compiler Flowchart

```mermaid
flowchart LR
    A[Pythonic Surface API] --> B[Decorators and Builders]
    B --> C[Sy Objects]
    C <--> D[Canonical IR Text]
    D <--> E[IR Parser and Printer]
    C --> F[Semantic Definitions]
    F --> G[Compiler Actions]
    G --> H[TraceDB and Evidence]
```

## Surface Construction And IR Parsing

```text
surface_api:
  many modular Python construction APIs
  accepts human/LLM-friendly builder/decorator authoring
  shares insertion context, diagnostics, symbol/type helpers, and evidence
  emits native Sy objects and canonical IR evidence

ir_parser:
  one canonical parser family
  copied/adapted from xDSL's parser/printer
  strictly follows MLIR/xDSL generic and custom operation syntax
```

## Code Sketches

Operation syntax should use real MLIR-style dialect names:

```mlir
"builtin.module"() ({
  func.func @add_one(%x: i32) -> i32 {
    %c1 = arith.constant 1 : i32
    %y = arith.addi %x, %c1 : i32
    func.return %y : i32
  }
}) : () -> ()
```

Surface construction evidence contract:

```python
built = construct_surface(add_one)
assert built.ir_text == expected_ir
assert built.evidence.builder_for("x + 1").owner is ArithAddiOp
assert roundtrip(built.ir).semantic_hash == built.ir.semantic_hash
```

General semantic database sketch:

```text
(syntax, facts_in, db_in) relation (facts_out, db_out)

TraceDB event/fact relations may include:
  execution events
  abstract facts
  semantic state facts
  effect facts
  obligation-like facts
  diagnostic facts/events
  eqsat operation saturation facts/evidence
  backend evidence facts
  LLM-agent review facts
```

First-slice `TraceDB` schema decision:

```text
TraceRecord(record_id, kind, relation, subject, key, value, scope, owner,
            order, provenance, evidence, validity, supersedes, retracted_by)
RelationSchema(relation, key_type, value_type, merge_policy, retention_policy)
ProjectionSpec(name, reads, query)
```

Semantic resolution policy decision:

```text
default: conflict error
select_one: typed level priority
run_all: typed level order with write-conflict checks
composite: typed CompositeSemanticDef for intentional equal-specificity parts
```

Control-operation semantic sketch:

```text
ScfForOp.ConcreteValue:
  read bounds and loop-carried input facts
  for each induction value:
    run body region with block arguments
    read scf.yield values
    update carried facts
    record LoopIteration event
  write result facts

ScfWhileOp.ConcreteValue:
  run before region on current state
  read scf.condition condition and payload
  if true, run after region and continue with yielded state
  if false, write result facts from payload
```

E-graph operation/action sketch:

```text
IR fragment
  -> e-class/e-graph operations
  -> rewrite/rule schedule
  -> saturated e-graph IR
  -> cost-based extraction
  -> replacement IR plus TraceDB evidence
```

## Source Comparison

| Concern | MLIR | xDSL | v0 | IntelliC Decision |
| --- | --- | --- | --- | --- |
| Syntax owner | Dialect operations | Python operation classes | Custom typed payloads | MLIR/xDSL-derived `Sy` |
| Semantics owner | Traits/interfaces plus pass conventions | Interpreter implementations | Interpreter and semantic payloads | Thin level-keyed SemanticDef records over syntax and TraceDB |
| Human surface | Textual IR and dialect custom assembly | Python APIs and notebooks | Pythonic authoring and staged Python | `Surface := IR + Construction API` |
| Equality reasoning | Pattern rewrites | Embedded eqsat transforms | Not central | E-graph/equality-saturation operations plus action model |
| Evidence | Round-trip text and lit tests | pytest/lit examples | staged artifacts and replay | Examples become tests or evidence |
| Extensibility | Dialects | Dialects and operation classes | Dialects/frontends | Dialects cannot bypass `Sy + Se` verification |

## Semantics Reference Lessons

| Source | Lesson For IntelliC |
| --- | --- |
| xDSL interpreter | Concrete execution can dispatch by operation implementation, but IntelliC should generalize beyond one interpreter hook. |
| xDSL SCF interpreter | Control operations do not need a separate semantic registry path; their implementations schedule regions, bind block arguments, and consume terminator results. |
| Fjfj paper | Modular semantics may require language restrictions and trace structures so behavior can be characterized one method/rule at a time instead of by exponential concurrent combinations. |
| egg | Equality reasoning should be handled by e-graphs, rewrites, analyses, costs, extraction, and explanations. |
| egglog | A relational rules/schedule model can combine equality saturation with Datalog-style facts and incremental analyses. |
| xDSL eqsat | E-classes can be embedded into IR, rewrites can be applied non-destructively, costs can be attached, and extraction can produce a chosen program. |

### Fjfj Trace-Semantics Details

Fjfj models a module as a labelled transition system with separate relations for
rules, value methods, and action methods. Rule and action-method relations
update module state; value-method relations observe state and return values.
These relations are partial, so their domains encode readiness, guards, and
abort behavior.

The formal evaluation judgments carry requested action calls, local variables,
and requested value calls. That tracked-call structure is paired with language
restrictions, especially the restriction that one logical cycle may request at
most one action method of a given submodule. This is the mechanism that lets
Fjfj avoid proofs over arbitrary subsets of simultaneous method calls.

For IntelliC, the transferable lesson is: semantic modularity may require
explicit restrictions and typed transition evidence, not just a richer metadata
object. The non-transferable part is the hardware-specific cycle/method model.
IntelliC should adapt Fjfj's partial-relation and trace-inclusion ideas into
operation/region `SemanticDef` relations and `TraceDB` projections.

## Decision Trace

```text
Need human-friendly authoring
  -> keep modular Surface construction APIs
Need agent-friendly review
  -> require canonical IR text, examples, TraceDB, and evidence
Need MLIR ecosystem alignment
  -> strictly match MLIR/xDSL syntax and copy/adapt xDSL classes
Need missing MLIR semantics gap closed
  -> make thin extensible level-keyed SemanticDef records and TraceDB first-class
Need transform equivalence
  -> model eqsat as operations/actions, learning first from xDSL eqsat
Need pass simplicity
  -> unify analysis/rewrite/pass/gate/execution/LLM review as actions
Need agent-safe mutation
  -> classify actions as Fixed or AgentAct
  -> keep AgentEvolve as a JIT-like workflow that generates Fixed actions
  -> record MutationIntent in TraceDB and apply it only through MutatorStage
Need pipeline replay
  -> use one logical TraceDB per pipeline run with action frames and checkpoints
```

## Extracted Lessons

- MLIR's strongest reusable idea is its uniform syntax model: dialects own
  operations, and operations uniformly contain operands, results, successors,
  properties, attributes, and regions.
- MLIR regions make nested program structure explicit while leaving region
  semantics to the containing operation. This is a useful split for IntelliC because
  scheduling, graph, and control-flow regions should not be forced into one
  execution model.
- MLIR ODS keeps operation facts in one declarative record for documentation,
  building, parsing, printing, verification, and tooling. IntelliC should preserve
  the "one operation specification" idea, but extend it with executable
  semantics.
- MLIR attributes and types are open extension points. IntelliC should keep them
  immutable and explicit enough for round-trip text, tests, and agent review.
- xDSL shows that the MLIR syntax model can live ergonomically in Python, with
  `Operation`, `Region`, `Block`, `Attribute`, and `TypeAttribute` classes.
- xDSL's interpreter shows a practical shape for executable semantics:
  implementation functions dispatch by operation type, receive Python runtime
  values for operands, and return Python runtime values for results. IntelliC should
  use that as one semantic definition level, not as the only semantic shape.
- xDSL's SCF interpreter shows the essential control-flow pattern: `scf.if`
  selects a child region, `scf.for` repeatedly runs a body region with an
  induction variable and loop-carried values, and `scf.yield` returns values to
  the containing control operation. The same shape should be expressed in
  IntelliC as operation-owned `SemanticDef` records using a shared region runner.
- MLIR SCF is broader than the current xDSL operation subset. IntelliC should
  support the full SCF dialect contract, including `scf.forall` and
  `scf.forall.in_parallel`, while still using xDSL's Python-native operations
  where available.
- Affine is central to optimization. xDSL provides a good Python-native base for
  affine expressions, maps, sets, and common affine ops, but MLIR's affine
  operation definitions are the completeness target. IntelliC should treat
  affine maps/sets, affine memory-access facts, and transform legality evidence
  as first-class design contracts.
- The Fjfj paper shows that semantic modularity may come from a combination of
  restrictions, partial transition relations, and tracked calls/events. IntelliC
  should consider a shared semantic state/fact/event database before freezing
  specific effect or obligation fields.
- egg and egglog show that equivalence should be a saturation mechanism with
  rules, analyses, schedules, cost models, extraction, and explanations rather
  than a field on each operation's semantics.
- xDSL's eqsat implementation shows an IR-embedded equality-saturation flow:
  create e-classes, apply PDL-derived rewrites non-destructively, add costs, and
  extract the chosen program. This should be modeled as operations/actions, not
  as a `SemanticDef` level.
- xDSL's developer docs prefer small examples plus lit/pytest evidence. This
  matches the IntelliC harness rule that design examples must become tests or
  evidence.
- `origin/htp/v0` proves that human-readable Python surfaces, staged artifacts,
  replay, typed semantic state, and interpreter-backed execution make compiler
  work easier for humans and agents. The clean design should keep those goals
  while replacing the custom v0 syntax substrate with an MLIR/xDSL-derived one.
- v0 also shows a risk: if semantics live as scattered metadata payloads,
  examples become hard to inspect and tests become indirect. The clean design
  should define `Se` next to `Sy` for every operation.

## Decisions Affected

- Define IntelliC's core principle as compiler participation by both human
  programmers and LLM agents.
- Treat `Surface` and `IR` as the practical concepts; keep `Lang` only as a
  classification term.
- Define `Surface := IR + Construction API`, where Python builders, decorators,
  operator hooks, and region helpers construct IR directly.
- Keep a strict MLIR/xDSL-compatible `ir_parser` for canonical IR text; do not
  make Pythonic authoring depend on parser-level composition.
- Define `IR := Sy + Se`, with MLIR/xDSL-derived syntax plus first-class
  thin extensible level-keyed SemanticDef records and TraceDB.
- Resolve the first semantics open questions with a small first slice:
  `TraceRecord` plus relation schemas/projections for `TraceDB`, typed
  resolution policies instead of implicit composition, a generated interpreter
  based on xDSL dispatch/region-runner ideas, direct `ctx.run_region`, offline
  checkpoint compaction, and xDSL-style equivalence operations before egglog.
- Define compiler actions with two action modes: `Fixed` for programmed
  behavior and `AgentAct` for directly agent-conducted scoped actions. Keep
  `AgentEvolve` outside `CompilerAction` as a JIT-like workflow that produces
  verified, versioned `Fixed` actions.
- Keep action `apply` non-mutating for syntax: it records facts, evidence, and
  `MutationIntent` rows in `TraceDB`; a `MutatorStage` later consumes accepted
  mutation intents and records applied or rejected outcomes.
- Keep shared pipeline lookup performance inside the authoritative pipeline
  `TraceDB`: extend relation indexes and materialized projections rather than
  adding a parallel pipeline-level analysis-cache subsystem.
- Allow actions to create auxiliary `TraceDB` instances for local computation,
  caching, or search, but require explicit export into the pipeline `TraceDB`
  before those results affect pipeline behavior.
- Provide typed agent-facing compiler APIs for `AgentAct`, such as scoped IR
  inspection, `TraceDB` queries, semantic-execution requests, match emission,
  review/diagnostic writes, mutation-intent proposals, and gate requests.
- Share one language-neutral `ActionHostAPI` and canonical `TraceRecord` /
  evidence-ref schema across Python actions and future C++ actions.
- Use one authoritative pipeline `TraceDB` per run, with action frames,
  transactions, checkpoints, and optional speculative overlays. Allow
  action-owned auxiliary `TraceDB` instances, but require explicit export before
  their results affect shared pipeline behavior.
- Treat the pipeline `TraceDB` as partly analogous to a classic analysis-cache
  system for cross-action derived facts, but broader because it also carries
  evidence, history, replay state, and gate inputs.
- Copy/adapt selected xDSL syntax and parser classes into native IntelliC instead of
  exposing wrappers around upstream xDSL modules.
- Use existing dialect names such as `builtin`, `func`, and `arith` in examples;
  IntelliC is not itself a dialect.
- Treat effects, obligations, diagnostics, and agent review as typed `TraceDB`
  event/fact relations or projections until examples prove a dedicated
  abstraction is required.
- Model eqsat/e-graph reasoning as explicit IR operations plus actions. Learn
  first from xDSL eqsat; keep egg and egglog as later engine references.
- Use concrete examples as design contracts and require each one to map to an
  automated test or named evidence artifact.

## Follow-Up Evidence

- Surface evidence should cover decorators, builders, operator hooks, region
  helpers, and strict IR parsing.
- Round-trip evidence should parse, print, and reparse canonical IR without
  semantic hash changes.
- Semantics evidence should show multiple extensible level keys can apply to one
  operation, and level-set selection detects conflicts unless composition is
  explicit.
- Resolution evidence should cover typed `select_one`, typed `run_all`,
  explicit composite definitions, and write-conflict failure.
- `TraceDB` evidence should show effects/obligations/diagnostics as shared
  semantic database records, plus `current`, `history`, retraction,
  supersession, and checkpoint compaction behavior.
- E-graph evidence should first cover xDSL-style operation-modeled eqsat, then
  compare egg and egglog integration paths if an external engine is needed.
- Pass evidence should show `Fixed` and `AgentAct` actions, `AgentEvolve`
  fixed-action generation jobs, typed match records, pending mutation intent
  failure, mutator-stage success, agent API calls, and one logical pipeline
  `TraceDB` with checkpoints.
- Indexing evidence should show hot relation/projection lookups served through
  `TraceDB` indexes or checkpoint materializations rather than side caches.
- Auxiliary-database evidence should show an action-private `TraceDB` exporting
  selected facts/evidence into the authoritative pipeline `TraceDB`.
- Cross-language evidence should show Python and native actions emitting the
  same canonical match, record, and evidence-reference shapes.
