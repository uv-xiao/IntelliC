# Design: Compiler Semantics

> Review status: Draft only. Not reviewed or approved. This document records
> current working direction and fix advice for IntelliC; do not treat it as
> accepted architecture until explicit human review approves it.

## Goal

Define `Se`, the semantics half of IntelliC IR:

```text
IR := Sy + Se
```

`Se` should make IntelliC useful as an intelligent compiler infrastructure, not just
a syntax tree library. Semantics should enable execution, replay, abstract
interpretation, pass validation, equality-saturation evidence, backend
evidence, diagnostics, and LLM-agent reasoning.

## Why Semantics Matter

Semantics are the mechanism that lets IntelliC answer questions like:

- What does this operation or region mean?
- Can this example execute or replay?
- What facts can an analysis derive without concrete execution?
- Did this rewrite preserve meaning?
- Which backend or proof artifact owns an opaque behavior?
- What semantic database facts, events, and evidence explain a pass pipeline to
  a human or LLM agent?

MLIR and xDSL give strong syntax infrastructure. xDSL also has an interpreter,
which is useful experience. IntelliC needs a broader semantic architecture where
execution, abstraction, semantic database interpretation, operation-modeled
equality reasoning, and backend evidence can coexist.

## Decision

Do not require one semantic definition per operation. A single operation may
have multiple semantic definitions, and a semantic definition may cover a family of
operations or a region convention.

Semantic definitions should be thin and tightly bound to typed syntax
definitions. A specific operation or dialect class contributes small
`SemanticDef` records tagged by extensible typed semantic levels. Example
levels include `ConcreteValue`, `AbstractRange`, `Symbol`, and `Backend`, but
the set is not fixed by the core framework. The compiler asks a semantic
registry for definitions matching a typed syntax key and a requested level or
level selection; it does not use string names or string references as
registration keys.

Semantics should run through a shared semantic state/fact/event database. To
avoid redundant storage concepts, the database should have only two primitive
semantic record kinds: ordered events and queryable facts. Semantic state,
diagnostics, evidence links, obligations, ranges, symbols, eqsat operation
evidence, and agent notes are typed fact/event relations or projections over
those records.

Examples:

```text
arith.addi:
  concrete execution model
  abstract integer/range model
  eqsat operation evidence
  backend lowering evidence model

func.func:
  callable-region operational model
  symbol-table model

builtin.module:
  top-level containment and symbol model
```

`execute` and `abstract` should not be hardcoded fields on one semantic record.
They are different semantic definitions or interpreters over the same syntax.

## Defining Semantics For IR And Operations

The high-level unit is a semantic definition:

```text
SemanticDef
  owner: OperationDef | DialectDef | IRDef | RegionConvention
  level: SemanticLevelKey
  reads: TraceDB relations/projections
  writes: TraceDB event/fact relations
  apply(scope, db_in) -> db_out or outputs, db_out
```

There are only two structural ideas here:

- `owner` is a typed syntax object, not a string name.
- `level` is an extensible typed semantic level key, not a string name or a
  fixed enum variant.

Everything else is an implementation contract over `TraceDB`. This keeps the
authoring model thin while still allowing one operation to have several semantic
definitions.

Semantic definitions should live on or next to operation and dialect
definitions, similar to how MLIR/xDSL bind syntax facts to operation classes.
A registry may index them for lookup, but registration keys must be typed
operation/dialect/level objects. Textual operation names such as `arith.addi`
are serialization and diagnostics data, not semantic ownership.

### Tiny Operation-Owned Examples

All examples use typed operation owners and typed semantic level keys:

```text
SomeOp.semantic(level=SomeLevel)(definition_function)
```

The examples also use typed `TraceDB` relation tokens such as `ValueConcrete`
and `ValueRange`. Those relation tokens are schema keys for database rows; they
are not string registration keys for semantics.

#### `arith.constant`: attribute to semantic fact

```python
@ArithConstantOp.semantic(level=ConcreteValue)
def constant_value(op, db):
    value = op.value.data
    db.put(ValueConcrete(subject=op.result, value=value))
    db.event(Evaluated(op=op, results=(op.result,)))

@ArithConstantOp.semantic(level=AbstractRange)
def constant_range(op, db):
    value = op.value.data
    db.put(ValueRange(subject=op.result, lower=value, upper=value))
```

Feature shown: an operation can define semantics by reading its typed syntax
fields and writing semantic facts for its results. No parser hook or operation
name string is involved.

#### `arith.addi`: same owner, different levels

```python
@ArithAddiOp.semantic(level=ConcreteValue)
def addi_value(op, db):
    lhs = db.require(ValueConcrete, op.lhs)
    rhs = db.require(ValueConcrete, op.rhs)
    db.put(ValueConcrete(subject=op.result, value=lhs.value + rhs.value))
    db.event(Evaluated(op=op, results=(op.result,)))

@ArithAddiOp.semantic(level=AbstractRange)
def addi_range(op, db):
    lhs = db.require(ValueRange, op.lhs)
    rhs = db.require(ValueRange, op.rhs)
    db.put(ValueRange(
        subject=op.result,
        lower=lhs.lower + rhs.lower,
        upper=lhs.upper + rhs.upper,
    ))
```

Feature shown: one operation owner contributes several small semantic
definitions. Concrete value semantics and abstract range semantics coexist
without a large semantic-definition object model.

#### `func.return`: terminator to region result

```python
@FuncReturnOp.semantic(level=ConcreteValue)
def return_value(op, db):
    values = tuple(db.require(ValueConcrete, operand) for operand in op.operands)
    region = op.parent_region
    db.event(RegionReturned(region=region, values=values, terminator=op))
    db.put(RegionResult(region=region, values=values))
```

Feature shown: terminator semantics are still operation-bound. The containing
operation, such as `FuncOp`, can later define how to interpret the returned
region result.

Verification mapping: registry evidence resolves typed owners such as
`ArithConstantOp`, `ArithAddiOp`, and `FuncReturnOp` at typed levels such as
`ConcreteValue` and `AbstractRange`, then checks that each definition writes the
declared `TraceDB` facts/events.

### Control Operation Definitions

Control operations such as `scf.if`, `scf.for`, `scf.while`, and
for-each/forall-style operations are not special at the registry level. They are
ordinary operation owners with ordinary `SemanticDef` records. They are special
only in what their definitions do: they schedule nested regions, bind block
arguments, read terminator facts, update loop-carried facts, and record control
events.

The operation-owned definition should use an interpreter or analysis context to
run child regions:

```text
ctx.run_region(region, inputs, db, convention) -> RegionResult facts/events
```

That `ctx.run_region` helper is not a second semantic system. It is the
generated interpreter or action runner applying the same selected `SemanticDef`
records inside a child region.

Concrete `scf.for` shape:

```python
@ScfForOp.semantic(level=ConcreteValue)
def scf_for_value(op, db, ctx):
    lb = db.require(ValueConcrete, op.lb).value
    ub = db.require(ValueConcrete, op.ub).value
    step = db.require(ValueConcrete, op.step).value
    carried = tuple(db.require(ValueConcrete, arg).value for arg in op.iter_args)

    for iv in range(lb, ub, step):
        result = ctx.run_region(
            op.body,
            inputs=(iv, *carried),
            db=db,
            convention=LoopBodyRegion,
        )
        carried = result.yielded_values
        db.event(LoopIteration(op=op, index=iv, yielded=carried))

    db.put(ValueConcreteTuple(subject=op.results, values=carried))
```

Concrete `scf.while` shape:

```python
@ScfWhileOp.semantic(level=ConcreteValue)
def scf_while_value(op, db, ctx):
    state = tuple(db.require(ValueConcrete, arg).value for arg in op.arguments)

    while True:
        before = ctx.run_region(
            op.before_region,
            inputs=state,
            db=db,
            convention=WhileBeforeRegion,
        )
        cond, *payload = before.condition_values
        db.event(LoopCondition(op=op, value=cond, payload=tuple(payload)))

        if not cond:
            db.put(ValueConcreteTuple(subject=op.results, values=tuple(payload)))
            return

        after = ctx.run_region(
            op.after_region,
            inputs=tuple(payload),
            db=db,
            convention=WhileAfterRegion,
        )
        state = after.yielded_values
```

For-each/forall-style control has the same shape, but the operation definition
must declare its scheduling contract:

```python
@ForEachOp.semantic(level=ConcreteValue)
def foreach_value(op, db, ctx):
    values = db.require(CollectionConcrete, op.values).items
    for index, value in enumerate(values):
        ctx.run_region(
            op.region,
            inputs=(value,),
            db=db,
            convention=ForEachElementRegion,
        )
        db.event(ForEachElement(op=op, index=index))
```

If a for-each operation is unordered or parallel, its semantic definition must
declare isolation, reduction, or commutativity requirements. Otherwise the
runner should treat it as ordered.

Abstract control semantics use the same owner-bound shape, but with different
scheduling:

- `scf.if` runs both branch regions and joins their facts when the condition is
  unknown.
- `scf.for` seeds induction-variable and loop-carried abstract facts, runs the
  body through a declared join/widening policy, and writes result facts.
- `scf.while` iterates `before` and `after` region facts to a fixpoint or fails
  if no widening/fuel policy is declared.
- for-each/forall-style operations summarize per-element facts and require a
  declared order, isolation, or reduction contract.

Terminator operations such as `scf.yield` and `scf.condition` are also ordinary
operation-owned semantic definitions, but they are only meaningful under a
compatible containing operation or region convention.

### Registry

Semantic definitions live in a simple registry:

```text
registry.lookup(owner, level) -> matching SemanticDef records
registry.resolve(owner, level_selection) -> selected SemanticDef records
```

Resolution contracts:

- Lookup keys are typed owner objects and typed semantic level keys.
- String operation names are never registry keys; they are only printed names,
  parse results, or diagnostics.
- More specific owners normally outrank broad defaults.
- Different levels coexist.
- Multiple definitions for the same owner and level require an explicit
  ordering or composition rule.
- A level selection may request one level key or a set of allowed level keys.
  Selection is checked for conflicts before mutation or execution.
- Missing required definitions fail before mutation or execution.
- Lookup results are recorded as evidence when a pipeline action uses them.

### Resolution Policies

Do not add a general parser-like composition calculus for semantics. The first
slice should support only explicit, typed resolution policies:

```python
registry.resolve(
    owner=ArithAddiOp,
    level_selection={Symbol, AbstractRange},
    policy=ResolutionPolicy.run_all(
        level_order=(Symbol, AbstractRange),
        write_conflicts=WriteConflict.ERROR,
    ),
)

registry.resolve(
    owner=SomeOp,
    level_selection={FastConcreteValue, ConcreteValue},
    policy=ResolutionPolicy.select_one(
        priority=(FastConcreteValue, ConcreteValue),
    ),
)
```

Default policy is `Conflict.ERROR`. If one owner/level lookup finds several
definitions with equal typed specificity, resolution fails unless the IR author
registered a typed composite definition:

```python
CompositeSemanticDef(
    owner=SomeOp,
    level=AbstractRange,
    parts=(BaseRangeDef, OverflowRefinementDef),
    mode=ComposeMode.SEQUENCE,
    write_conflicts=WriteConflict.ERROR,
)
```

This keeps normal operation semantics thin. Composition is visible as a typed
definition, not hidden in string names or registration order.

### Level Selection

Semantic levels are open typed keys. Dialects, IR packages, tools, or later
verification backends may define new levels without changing the core registry:

```python
ConcreteValue = SemanticLevelKey("concrete.value")
AbstractRange = SemanticLevelKey("abstract.range")
Symbol = SemanticLevelKey("symbol")
BackendEvidence = SemanticLevelKey("backend.evidence")
```

The string-like spelling above is only construction/debug metadata for the typed
key object. It is not used as the registry key.

A pipeline action can select one level:

```text
level_selection = ConcreteValue
```

or an allowed set:

```text
level_selection = {ConcreteValue, AbstractRange}
```

Set selection is useful when a pipeline can accept several semantic views, but
it must still be deterministic. For one owner, if the selected level set matches
two definitions and the action did not provide a composition or preference rule,
resolution fails:

```text
owner=ArithAddiOp
available definitions: ConcreteValue, AbstractRange
selection={ConcreteValue, AbstractRange}
composition=none
=> conflict: two selected definitions for one owner
```

An action that intentionally wants both levels must say so explicitly:

```text
selection={ConcreteValue, AbstractRange}
policy=ResolutionPolicy.run_all(
  level_order=(ConcreteValue, AbstractRange),
  write_conflicts=WriteConflict.ERROR,
)
```

This keeps the definition model thin while avoiding a fixed global level enum.

### Semantic Polymorphism

Semantic definition polymorphism is typed dispatch over semantic owners and
levels. It should feel close to MLIR/xDSL operation ownership, but generalized
from syntax facts to meaning:

```text
lookup request:
  owner = type(op) | typed interface | dialect | IR | region convention
  level_selection = one SemanticLevelKey or a set of allowed SemanticLevelKeys
  constraints = optional typed predicates over types, traits, or attributes
```

The important forms are:

| Form | Example | Meaning |
| --- | --- | --- |
| Same owner, different level | `ArithAddiOp` at `ConcreteValue` and `AbstractRange` | One operation has several semantic views |
| Exact owner override | `ArithAddiOp` overrides `IntegerBinaryOpInterface` | A specific operation can specialize a broader rule |
| Interface fallback | `IntegerBinaryOpInterface` at `AbstractRange` | A family of typed operations can share semantics |
| Dialect default | `ArithDialect` at `Backend` | A dialect can provide broad evidence or lowering policy |
| Region convention | `CallableRegion` at `ConcreteCall` | Region behavior is shared without making `Region` syntax semantic |

Resolution is ordered by typed specificity:

```text
exact operation owner
  > typed operation interface or trait owner
  > containing dialect owner
  > IR definition owner
  > explicit region convention owner
```

This is polymorphism, but not string-based dispatch. `arith.addi` may appear in
printed IR or diagnostics; registry lookup uses `ArithAddiOp`,
`IntegerBinaryOpInterface`, `ArithDialect`, and typed semantic level keys or
level selections.

Example:

```python
@IntegerBinaryOpInterface.semantic(level=AbstractRange)
def integer_binary_range(op, db):
    lhs = db.require(ValueRange, op.lhs)
    rhs = db.require(ValueRange, op.rhs)
    return op.abstract_range(lhs, rhs, db)

@ArithAddiOp.semantic(level=AbstractRange)
def addi_range(op, db):
    lhs = db.require(ValueRange, op.lhs)
    rhs = db.require(ValueRange, op.rhs)
    db.put(ValueRange(
        subject=op.result,
        lower=lhs.lower + rhs.lower,
        upper=lhs.upper + rhs.upper,
    ))
```

Feature shown: `ArithAddiOp` can use a specific abstract-range rule, while a
future `ArithSubiOp` could fall back to the interface rule if it satisfies the
same typed interface contract. If two definitions match with equal specificity
and no composition rule, lookup fails.

### Interpreter Generation

Semantic definitions can generate an interpreter when a selected set of
semantic level keys forms an executable subset. The generated interpreter is a
typed dispatcher plus region runner over `TraceDB`; it is not a separate
hand-written execution system.

Generation shape:

```text
InterpreterSpec
  ir: IRDef
  level_selection: {ConcreteCall, ConcreteValue}
  entry convention: FuncOp at ConcreteCall
  operation semantics: registry-selected SemanticDef records
  region semantics: registry-selected region convention definitions
  state carrier: TraceDB
```

Build process:

1. Choose an IR definition and executable level selection, usually
   `{ConcreteCall, ConcreteValue}` for callable regions.
2. Collect operation and region owners reachable in the selected scope.
3. Resolve each `(owner, level)` through the semantic registry, using typed
   polymorphic fallback when needed.
4. Validate that selected definitions declare their `TraceDB` reads/writes and
   can run deterministically for the chosen interpreter mode.
5. Generate or cache a dispatch table from typed operation classes and region
   conventions to selected `SemanticDef.apply` functions.
6. Run regions by seeding input facts, applying operation definitions in the
   region's semantic order, and reading the region result facts/events.

Tiny generated-interpreter example:

```python
simple_arith_interp = Interpreter.from_semantics(
    ir=SimpleArithIR,
    entry=FuncOp,
    levels=(ConcreteCall, ConcreteValue),
)

result = simple_arith_interp.call("add_one", 41)
assert result == 42
```

The interpreter is generated from these selected definitions:

```text
FuncOp          level=ConcreteCall
ArithConstantOp level=ConcreteValue
ArithAddiOp     level=ConcreteValue
FuncReturnOp    level=ConcreteValue
CallableRegion  level=ConcreteCall
```

Execution evidence:

```text
seed  ValueConcrete(subject=%x, value=41)
apply ArithConstantOp.ConcreteValue -> ValueConcrete(subject=%c1, value=1)
apply ArithAddiOp.ConcreteValue     -> ValueConcrete(subject=%y, value=42)
apply FuncReturnOp.ConcreteValue    -> RegionReturned(values=(42,))
read  RegionResult(func.body)       -> 42
```

Other levels can generate related engines, but with different scheduling rules:

- `AbstractRange` can generate an abstract interpreter or analysis action. It
  may need joins and fixpoint iteration for loops.
- `Backend` can generate a lowering/evidence action, not direct execution.

Equality saturation is not generated from a semantic level. It is an IR/action
mechanism over explicit eqsat operations.

If any required operation or region convention has no selected definition, or
if two polymorphic definitions match without a deterministic resolution rule,
interpreter generation fails before execution.

First interpreter runtime scope:

- Copy/adapt xDSL's typed operation dispatch, region execution protocol,
  terminator return protocol, and listener hooks.
- Use IntelliC `SemanticDef` selection and `TraceDB` as the state carrier
  instead of xDSL's public interpreter API.
- Support function call, straight-line regions, `scf.if`, `scf.for`,
  `scf.while`, and yield/return/condition terminators in the first executable
  semantic slice.
- Record selected definitions, region entry/exit, terminator results, loop
  iterations, and returned values as evidence.
- Defer optimized JIT/codegen, full external-call integration, advanced memory
  models, and every upstream xDSL dialect implementation.

The implementation should learn from xDSL's interpreter shape, not expose xDSL
as IntelliC's public interpreter dependency.

### IR-Level Semantics

An IR chooses a list of semantic definitions:

```text
simple_arith_ir semantics:
  BuiltinModuleOp: Symbol
  FuncOp: Symbol, ConcreteCall
  ReturnOp: ConcreteValue
  ArithConstantOp: ConcreteValue, AbstractRange
  ArithAddiOp: ConcreteValue, AbstractRange
```

Feature shown: an IR-level semantic design is just the set of definitions it
enables for its dialects and operations. It does not need a separate composition
object unless implementation later proves useful.

Verification mapping: `add_one` evidence shows lookup for each operation and
level before execution or abstract interpretation.

### Region Semantics

Region semantics should be defined by the containing operation or a named region
convention, not by `Region` syntax itself. For example:

- `func.func` provides `region.callable` for its body.
- `scf.if` provides branch selection and yield behavior for then/else regions.
- `scf.for` provides induction-variable binding, loop-carried value update, and
  iteration scheduling for its body region.
- `scf.while` provides before/after region scheduling, condition handling, and
  loop-carried state update.
- for-each/forall-style operations provide element binding plus an ordering,
  isolation, or reduction contract for the element region.
- `builtin.module` provides top-level containment and symbol visibility.

This preserves the syntax/semantics split: syntax stores regions, while semantic
definitions define how those regions run, yield, branch, or scope symbols.

### Control-Region Runner API

Expose direct region execution first:

```python
result = ctx.run_region(
    region=op.body,
    inputs=(iv, *carried),
    db=db,
    convention=LoopBodyRegion,
)
```

Return a typed result object:

```text
RegionRunResult
  kind: yielded | returned | condition | branch | fallthrough
  values: tuple
  successor: Block | None
  terminator: Operation | None
  db: TraceDB
```

Operation definitions consume only the result kinds allowed by their region
convention. For example, `scf.for` expects `yielded`, `func.func` expects
`returned`, `scf.while` expects `condition` from `before_region` and `yielded`
from `after_region`, and `cf` operations may use `branch`.

Do not expose a separate continuation API in the first slice. Continuation-like
objects may exist internally to implement multi-block CFGs, but operation
authors should start with `ctx.run_region` and typed `RegionRunResult`.

## Semantic Database

Use a shared semantic database, named `TraceDB` until implementation chooses a
better package name:

```text
TraceDB
  events: ordered append-only records of what happened
  facts: indexed relation records for what holds or is known
  projections: named query views over events and facts
```

`TraceDB` is not only a log. It is the shared semantic state and query substrate.
Semantic definitions update it; actions and gates query it; evidence and agents
cite it. Ordered events preserve replay and explanation order, while fact
relations support state, checks, analyses, diagnostics, evidence, and agent
review.

Do not add independent top-level stores for diagnostics, evidence links,
provenance, or state cells unless examples prove the record model is too weak.
Those concepts should start as relations:

| Concept | Representation |
| --- | --- |
| Semantic state | current or versioned facts keyed by state name and subject |
| Diagnostics | diagnostic facts or events tied to Sy/evidence ids |
| Evidence links | evidence facts connecting Sy, construction, pass, backend, or proof ids |
| Provenance | required metadata on every event/fact record |
| Effects/obligations | projections over event/fact relations |
| Ranges/symbols/types | domain-specific fact relations |
| Eqsat/e-graph operation evidence | facts/events linked to e-class operations, costs, saturation, and extraction |

The database should stay structured enough for deterministic tests and
agent-readable review. Public semantic APIs should read and write typed records
or relation rows rather than ad hoc dictionaries, except at explicit
serialization boundaries.

### First-Slice TraceDB Schema

The minimal schema is one record table plus typed relation schemas and
projections. Do not create separate top-level stores for diagnostics, evidence,
effects, analysis caches, or agent notes.

```text
TraceRecord
  record_id
  kind: event | fact
  relation: RelationKey
  subject: typed syntax/evidence/artifact id
  key: typed tuple
  value: typed payload
  scope
  owner
  order
  provenance
  evidence
  validity: asserted | derived | retracted | superseded
  supersedes: record_id | None
  retracted_by: record_id | None
```

Supporting metadata:

```text
RelationSchema
  relation: RelationKey
  key_type
  value_type
  merge_policy
  retention_policy

ProjectionSpec
  name
  reads: relation keys
  query(db) -> typed view
```

Required indexes for the first slice:

- `(relation, subject)` for current semantic facts.
- `(relation, key)` for relation-specific lookups.
- `(scope, order)` for replay and evidence review.
- `(owner, relation)` for checking declared reads/writes.
- `record_id` for provenance, retraction, supersession, and evidence links.

This schema supports concrete values, abstract facts, eqsat evidence, backend
evidence, diagnostics, and LLM-agent notes as typed relations over the same
primitive records.

## SemanticDef Relation Shape

IntelliC should treat semantics as programmable transition or interpretation
relations over syntax and `TraceDB`:

```text
SemanticDef relation:
  (scope, inputs, db_in) -> (outputs, db_out)
```

The semantic database is the general carrier. It can represent effects,
obligations, diagnostics, proof hints, abstract facts, execution events, backend
evidence, or LLM-agent review comments as `TraceRecord` rows without forcing
all of those into fixed fields on every operation.

Specific projections such as "effects" or "obligations" can be derived from
database events and facts, including state facts, when needed. They should not
be premature mandatory fields on every semantic result.

### Retraction And Supersession

`TraceDB` should support deletion-like behavior, but normal semantic execution
should not physically delete records. The default operation is logical
retraction or supersession:

```text
assert fact:
  put ValueRange(subject=%x, lower=0, upper=10)

retract fact:
  retract ValueRange(subject=%x) reason=branch_refined

supersede fact:
  supersede ValueRange(subject=%x, lower=0, upper=10)
        with ValueRange(subject=%x, lower=3, upper=7)
        reason=constraint_applied
```

Reasoning:

- Events should stay append-only so replay and evidence remain inspectable.
- Facts should be versioned relation rows; "current facts" are a projection that
  hides retracted or superseded rows by default.
- Retraction is useful for branch refinement, invalidated analysis facts,
  speculative facts, rewrite/extraction replacement, and diagnostic withdrawal.
- Physical deletion is only a storage/compaction concern after an evidence
  boundary proves no retained artifact cites the record.

Minimal API shape:

```text
db.put(fact, provenance)
db.retract(fact_key, reason, provenance)
db.supersede(old_fact_key, new_fact, reason, provenance)
db.current(Relation, subject) -> live facts
db.history(Relation, subject) -> asserted/retracted/superseded facts
```

Feature shown: the database has deletion semantics without losing auditability.
Most consumers query `current`; replay, debugging, and agent review can query
`history`.

### Retention And Compaction

Physical deletion is not a normal semantic operation. It is an offline storage
operation over a checkpointed database:

```text
compact(db, checkpoint):
  require record is retracted or superseded
  require no retained evidence artifact cites record_id
  require current projections are materialized in checkpoint
  write RecordDigest(record_id, hash, relation, subject)
  write CompactionEvent(checkpoint, removed_record_ids)
  remove physical payload only after retention policy allows it
```

Default retention policy for active development is keep full history. A project
may enable compaction only for records that are stale, digest-preserved, and no
longer cited by retained evidence, diagnostics, backend artifacts, or review
notes.

## TraceDB-Updating Semantics

A semantic definition should be able to define how the semantic database changes:

```text
(op, inputs, db_in) -> (outputs, db_out)
```

or, more generally:

```text
(syntax, facts_in, db_in) relation (facts_out, db_out)
```

This leaves room for several styles:

- concrete operational semantics
- abstract interpretation
- database/trace semantics
- rule-based transition systems
- symbolic facts consumed by eqsat actions
- backend evidence semantics
- LLM-agent review actions that append evidence and review facts

Semantic modularity may still require explicit restrictions in specific
domains, but those restrictions should be justified by IntelliC examples rather
than imported as a standalone trace-calculus section.

## Equality And E-Graph Operations

Do not put equivalence laws or e-graph rewrites into operation `SemanticDef`
records. Equality saturation should be modeled as explicit IR plus compiler
actions, similar to xDSL's eqsat flow.

- egg: e-graphs, rewrites, analyses, extraction, cost functions, explanations.
- egglog: equality saturation combined with Datalog-style rules, relations,
  schedules, extraction, and incremental/composable analyses.
- xDSL eqsat support: creating e-classes in IR, applying PDL-derived rewrites
  non-destructively, adding costs, and extracting the chosen program.

IntelliC should expose an operation-modeled eqsat flow:

```text
source IR fragment
  -> eqsat/equivalence operations such as graph, class, yield, rule, cost
  -> saturation action mutates/extends those operations non-destructively
  -> extraction action selects a replacement IR fragment
  -> TraceDB evidence records rules applied, costs, and extraction choice
```

With this mechanism, ordinary operations do not need to define equivalence
fields, and the semantic registry does not need an e-graph level. Semantic
definitions may still produce facts that eqsat actions consume, such as concrete
constants, abstract ranges, purity, or backend evidence. The e-graph itself is
represented by syntax operations and action evidence.

First eqsat operation slice:

```text
equivalence.graph       # region container for equality-saturation IR
equivalence.class       # e-class for equivalent SSA values
equivalence.const_class # e-class with known constant value
equivalence.yield       # graph result terminator
```

The first slice should also support `min_cost_index` and an operation cost
attribute or fact, following xDSL's extraction shape. Rewrite rules, saturation
schedules, extraction decisions, and explanation links are compiler-action
inputs and `TraceDB` evidence, not ordinary per-operation semantic levels.

Defer egglog integration until the xDSL-style operation-modeled flow can build
initial e-classes, apply at least one rewrite family, attach costs, extract a
chosen program, and record the evidence.

## Region Semantics

Do not invent placeholder project-specific dialect operations. Use MLIR/xDSL
dialect concepts such as `scf.if`, `cf.br`, `func.func`, and `builtin.module`
when examples need existing control-flow or containment operations.

Syntax holds regions. Semantic definitions define what a region means:

- `func.func` definitions: callable region and symbol behavior.
- `scf.if` definitions: chooses a region based on a condition and yields values.
- `scf.for` definitions: run a body region with an induction variable and
  loop-carried values.
- `scf.while` definitions: alternate before/after regions until a condition
  terminates the loop.
- for-each/forall-style definitions: run an element region with an explicit
  ordered, isolated, or reduction-based scheduling contract.
- `cf` definitions: branch/control-flow transition behavior.
- `builtin.module` definitions: top-level containment and symbols.

IntelliC can copy and adjust xDSL/MLIR dialect syntax first, then add semantic
definitions gradually.

## Contracts

- Semantics for an IR or operation are authored as thin `SemanticDef` records
  bound to typed operation, dialect, IR, or region-convention owners.
- A `SemanticDef` has a typed owner, an extensible typed semantic level key, declared
  reads/writes, and an apply relation over `TraceDB`.
- An operation may have zero, one, or many semantic definitions.
- Missing semantics is allowed only when the current pipeline does not require
  semantics for that operation, or when an explicit opaque evidence boundary is
  present.
- Semantic applicability is checked by registry lookup against a requested
  level, not by a global "one semantic def per op" rule.
- Registry lookup must use typed owner and level keys, not string names.
- Registry resolution may select one level or a set of allowed levels; if a set
  matches multiple definitions for one owner, an explicit composition or
  preference rule is required.
- Default semantic resolution policy is conflict failure; composition is allowed
  only through typed resolution policies or typed composite definitions.
- Semantic polymorphism resolves by typed specificity: exact operation,
  interface/trait, dialect, IR definition, then explicit region convention.
- Multiple definitions for the same owner and level require explicit ordering
  or composition.
- Interpreter generation is allowed only from selected semantic level keys whose
  definitions and region conventions form an executable subset.
- Region semantics are owned by containing-operation definitions or named region
  conventions, not by `Region` syntax itself.
- Control-flow operations are not registry-level special cases; their
  operation-owned semantic definitions schedule child regions, bind block
  arguments, consume terminator facts, and write result facts/events.
- Loop and for-each semantics must declare their scheduling contract, including
  ordered execution, isolation, reduction, fuel, join, or widening as applicable.
- The first interpreter runtime copies/adapts xDSL's dispatch, region runner,
  terminator protocol, and listener ideas, but exposes IntelliC `SemanticDef`
  selection and `TraceDB` as its public contract.
- Registry lookup results must be inspectable and recorded as evidence when used
  by a pipeline action.
- `TraceDB` has two primitive semantic record kinds: events and facts.
- The first `TraceDB` schema is a single `TraceRecord` table plus typed relation
  schemas, projections, and indexes over relation, subject, key, scope, owner,
  order, and record id.
- Semantic state, effects, obligations, diagnostics, proof hints, backend
  evidence, and LLM-agent notes are represented as typed event/fact relations or
  projections.
- Deletion-like behavior is represented by logical retraction or supersession
  facts/events; physical deletion is only storage compaction after evidence
  retention rules allow it.
- Physical compaction requires a checkpoint, digest preservation, and proof that
  no retained evidence artifact cites the removed records.
- Specific concepts like effects or obligations should be `TraceDB` projections
  unless a later design proves they need first-class dedicated storage.
- E-graph/equality reasoning is represented as IR operations plus compiler
  actions, not as a semantic level and not as per-op equivalence fields.
- The first eqsat operation set is `equivalence.graph`, `equivalence.class`,
  `equivalence.const_class`, and `equivalence.yield`, plus cost/extraction
  evidence carried by actions and `TraceDB`.
- Semantic definitions must be inspectable and cite evidence requirements.

## Failure Modes

- A pipeline requires a semantic level selection and no applicable definition
  exists:
  semantic lookup fails.
- A semantic definition is registered with a string operation name or string
  level instead of typed owner/level keys: registration fails.
- Two definitions match the same typed owner and level without ordering or
  composition: semantic lookup fails.
- A level-set selection matches two definitions for the same owner without an
  explicit composition or preference rule: semantic resolution fails.
- A `run_all` resolution policy selects definitions that write the same fact key
  without an explicit merge/supersession rule: semantic resolution fails.
- Two polymorphic definitions match with equal specificity and no deterministic
  tie-breaker: semantic lookup fails.
- Interpreter generation finds an operation or region convention without a
  required executable semantic definition: interpreter generation fails before
  execution.
- A selected semantic definition has undeclared reads/writes or an unsupported
  scheduling requirement for the requested interpreter mode: interpreter
  generation fails.
- A definition writes a relation that it did not declare: semantic schema
  validation fails.
- A region is interpreted without an applicable containing-operation or region
  convention definition: semantic lookup fails.
- A control operation tries to run a child region whose terminator facts do not
  match the containing operation's convention: region-result validation fails.
- `ctx.run_region` returns a result kind unsupported by the requesting operation
  convention: region-run validation fails.
- A concrete loop exceeds its declared fuel or cannot prove progress under the
  selected execution mode: execution fails with nontermination evidence.
- An abstract loop requires a fixpoint but has no declared join or widening
  policy: abstract interpretation planning fails before mutation.
- An unordered for-each body writes non-commutative state without isolation or
  reduction evidence: scheduling validation fails.
- A semantic definition writes a fact/event relation the consumer cannot read:
  semantic database schema validation fails.
- A pass depends on an effect/obligation projection that no semantic definition
  provides: action planning fails before mutation.
- A consumer reads a superseded or retracted fact through `current`: database
  projection validation fails.
- Physical deletion removes a record still cited by evidence or provenance:
  retention validation fails.
- Physical compaction lacks a checkpoint, digest, or retained-artifact citation
  check: compaction planning fails.
- Eqsat extraction changes syntax without extraction evidence: pipeline gate
  fails.
- Eqsat operations appear outside `equivalence.graph` or violate e-class
  ownership/type invariants: structural verification fails.
- Backend handoff sees opaque behavior without owner/evidence facts: handoff
  fails.

## Examples

### Example 1: Operation-Owned Semantic Definitions

```text
syntax:
  %c1 = arith.constant 1 : i32
  %y = arith.addi %x, %c1 : i32
  func.return %y : i32

semantic defs:
  owner=ArithConstantOp level=ConcreteValue
    write ValueConcrete(subject=%c1, value=1)

  owner=ArithAddiOp level=ConcreteValue
    read  ValueConcrete(subject=%x, value=41)
    read  ValueConcrete(subject=%c1, value=1)
    write ValueConcrete(subject=%y, value=42)

  owner=ArithAddiOp level=AbstractRange
    read  ValueRange(subject=%x, lower=0, upper=10)
    read  ValueRange(subject=%c1, lower=1, upper=1)
    write ValueRange(subject=%y, lower=1, upper=11)

  owner=FuncReturnOp level=ConcreteValue
    read  ValueConcrete(subject=%y, value=42)
    event RegionReturned(region=func.body, values=(42,))
```

Feature shown: each operation owns the semantic definitions for its local
meaning. `arith.addi` has multiple levels, while `func.return` bridges an
operation result into a region result.

Verification mapping: registry evidence shows `lookup(ArithAddiOp,
ConcreteValue)` and `lookup(ArithAddiOp, AbstractRange)` select different
definitions, while `ArithConstantOp` and `FuncReturnOp` lookup evidence shows
the surrounding straight-line function can execute.

### Example 2: IR-Level Semantics Are A Definition Set

```text
simple_arith_ir semantic defs:
  BuiltinModuleOp   level=Symbol
  FuncOp            level=Symbol
  FuncOp            level=ConcreteCall
  ReturnOp          level=ConcreteValue
  ArithConstantOp   level=ConcreteValue
  ArithConstantOp   level=AbstractRange
  ArithAddiOp       level=ConcreteValue
  ArithAddiOp       level=AbstractRange
```

Feature shown: an IR-level semantic design is the set of semantic definitions it
enables. No extra composition object is required at the design level.

Verification mapping: `add_one` evidence shows lookup for each operation and
level before concrete execution and abstract interpretation.

### Example 3: Generated Concrete Interpreter

```text
interpreter simple_arith_concrete:
  ir: SimpleArithIR
  levels: ConcreteCall, ConcreteValue
  dispatch:
    FuncOp          -> ConcreteCall SemanticDef
    ArithConstantOp -> ConcreteValue SemanticDef
    ArithAddiOp     -> ConcreteValue SemanticDef
    FuncReturnOp    -> ConcreteValue SemanticDef
    CallableRegion  -> ConcreteCall SemanticDef
```

Run evidence:

```text
call add_one(41)
seed  ValueConcrete(%x, 41)
apply ArithConstantOp -> ValueConcrete(%c1, 1)
apply ArithAddiOp     -> ValueConcrete(%y, 42)
apply FuncReturnOp    -> RegionReturned(values=(42,))
return 42
```

Feature shown: a concrete interpreter can be generated from selected
operation-bound semantic definitions plus region conventions. The interpreter is
a typed dispatch table over `SemanticDef.apply`, not a new operation-name
dispatch mechanism.

Verification mapping: interpreter-generation evidence records selected
definitions, rejected missing definitions, dispatch order, input facts, output
facts, and returned value.

### Example 4: TraceDB Carries Effects Without Dedicated Effect Fields

```text
%token = async-like-op(...)
await-like-op(%token)
```

TraceDB sketch:

```text
event create_token token=%token owner=async-like-op
event consume_token token=%token owner=await-like-op
fact token_consumed(%token)
```

Feature shown: "obligation" is a semantic database convention. A gate can query
events and facts for unconsumed tokens without every semantic result having an
`obligations` field.

Verification mapping: `TraceDB` schema evidence and a gate example that rejects a
missing `consume_token` event.

### Example 5: TraceDB Retraction And Supersession

```text
initial abstract fact:
  put ValueRange(subject=%x, lower=0, upper=10)

after branch condition %x > 2:
  supersede ValueRange(subject=%x)
        with ValueRange(subject=%x, lower=3, upper=10)
        reason=branch_refined

after leaving branch scope:
  retract ValueRange(subject=%x, lower=3, upper=10)
        reason=scope_closed
```

Query behavior:

```text
db.current(ValueRange, %x) -> no branch-local range after scope_closed
db.history(ValueRange, %x) -> original range, refined range, retraction event
```

Feature shown: deletion is needed semantically, but as logical retraction or
supersession. The database keeps replayable evidence while normal consumers see
only live facts.

Verification mapping: current/history projection evidence checks that retracted
facts disappear from `current` and remain available in `history`.

### Example 6: Control Operation Semantic Definitions

```text
semantic defs:
  owner=ScfForOp level=ConcreteValue
    read  ValueConcrete(%lb), ValueConcrete(%ub), ValueConcrete(%step)
    read  ValueConcrete(iter_args...)
    for each iv in range(lb, ub, step):
      run body with inputs=(iv, carried...)
      read RegionYield(body)
      write LoopIteration(op=scf.for, index=iv)
      update carried...
    write ValueConcreteTuple(results, carried...)

  owner=ScfForOp level=AbstractRange
    seed induction variable range
    seed loop-carried ranges
    run body with join/widening policy
    write ValueRange(result...)
```

For `scf.while`, the concrete definition alternates `before_region` and
`after_region`:

```text
state = initial operands
loop:
  run before_region(state)
  read ConditionResult(condition, payload...)
  if condition is false:
    write ValueConcreteTuple(results, payload...)
    stop
  run after_region(payload...)
  read RegionYield(after_region)
  state = yielded values
```

Feature shown: control operations are programmed as normal operation-owned
semantic definitions. Their definitions orchestrate region execution and
loop-carried state, while child operations still use normal typed semantic
dispatch.

Verification mapping: `sum_to_for(5) -> 10` evidence records `ScfForOp`
lookup, five body-region executions, five `scf.yield` result events, and the
final carried value. Abstract-loop evidence records the selected join/widening
policy.

### Example 7: E-Graph Operations And Actions

```egglog
(rewrite (Add a (Const 0)) a)
(rewrite (Mul a (Const 1)) a)
(run 4)
```

IntelliC eqsat IR/action sketch:

```text
equivalence.graph {
  %x_c = equivalence.class %x : i32
  %z_c = equivalence.const_class %zero (constant = 0 : i32) : i32
  %add = arith.addi %x_c, %z_c : i32
  %add_c = equivalence.class %add, %x_c : i32
  equivalence.yield %add_c : i32
}

action eqsat-saturate:
  append/merge equivalence.class operands
  record event rewrite_applied(rule=add-zero)

action eqsat-extract:
  choose min_cost_index
  replace original fragment
  record event extracted(cost_model=ast-size)
```

Feature shown: equality reasoning is operation-modeled IR plus actions. It is
not a `SemanticDef` level and not an equivalence field on each ordinary
operation.

Verification mapping: e-graph action evidence records e-class creation,
saturation, extraction, and selected replacement.

## Resolved Design Questions

- Minimal `TraceDB` schema: use one `TraceRecord` table with typed relation
  schemas, typed projections, validity fields, provenance, evidence, and indexes.
  Concrete values, abstract facts, eqsat evidence, backend evidence,
  diagnostics, and LLM-agent notes are relations over that table.
- Semantic composition syntax: default to conflict failure; use typed
  `ResolutionPolicy.select_one`, typed `ResolutionPolicy.run_all`, or a typed
  `CompositeSemanticDef` when equal-specificity definitions intentionally
  compose.
- First interpreter runtime: copy/adapt xDSL's dispatch, region execution,
  terminator return, and listener ideas, but expose IntelliC `SemanticDef`
  selection and `TraceDB` rather than xDSL's public interpreter API.
- Control-region runner API: expose direct `ctx.run_region(...)` returning a
  typed `RegionRunResult`; keep continuation objects internal until multi-block
  CFG examples require a public API.
- Retention policy: keep full history by default; physical compaction is an
  offline checkpoint operation requiring retraction/supersession, digest
  preservation, and retained-evidence citation checks.
- Minimal eqsat operation set: start with xDSL-style `equivalence.graph`,
  `equivalence.class`, `equivalence.const_class`, and `equivalence.yield`, plus
  action-owned cost/extraction evidence; defer egglog until this flow is proven.

## Planned Verification Evidence

- Focused source reading of xDSL eqsat operations/transforms before designing
  the first equality-saturation action; egg and egglog remain references for
  later engine choices.
- Semantic registry evidence for typed owner/level lookup on
  `ArithConstantOp`, `ArithAddiOp`, `FuncReturnOp`, and the `simple_arith_ir`
  definition set.
- Polymorphic lookup evidence showing exact operation semantics overriding a
  typed interface fallback without using string operation names.
- Generated-interpreter evidence for `add_one(41) -> 42`, including selected
  definitions, dispatch table, seeded facts, and returned region result.
- Control-operation evidence for `scf.for` and `scf.while`, including child
  region invocations, terminator facts, loop-carried values, and any fuel,
  join, or widening policy.
- Resolution-policy evidence showing `select_one`, `run_all`, and conflict
  failure for equal-specificity semantic definitions.
- TraceDB schema evidence showing concrete, abstract, diagnostic, backend,
  eqsat, and agent-review relations stored as typed records with `current` and
  `history` projections.
- Retraction/supersession evidence showing `current` hides stale facts while
  `history` preserves replayable provenance.
- Compaction evidence showing a checkpointed stale record replaced by a digest
  and rejected when retained evidence still cites the record id.
- Example `TraceDB` updates for concrete execution, abstract facts, token
  consumption, and eqsat operation extraction.
- Policy evidence that no design asserts one semantic definition per operation.

## Out Of Scope

- Full formal proof system in the first implementation.
- Selecting one final trace/database calculus before more examples are studied.
- Backend-specific semantic definitions beyond explicit opaque/evidence boundaries.
- Optimized interpreter/JIT generation; the first generated interpreter can be a
  typed Python dispatch table over selected semantic definitions.
- Per-operation equivalence fields as the primary equivalence mechanism.
