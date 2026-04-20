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
interpretation, pass validation, equality saturation, backend evidence,
diagnostics, and LLM-agent reasoning.

## Why Semantics Matter

Semantics are the mechanism that lets IntelliC answer questions like:

- What does this operation or region mean?
- Can this example execute or replay?
- What facts can an analysis derive without concrete execution?
- Did this rewrite preserve meaning?
- Which backend or proof artifact owns an opaque behavior?
- What trace explains a pass pipeline to a human or LLM agent?

MLIR and xDSL give strong syntax infrastructure. xDSL also has an interpreter,
which is useful experience. IntelliC needs a broader semantic architecture where
execution, abstraction, trace interpretation, equality reasoning, and backend
evidence can coexist.

## Decision

Do not require one semantic definition per operation. A single operation may
have multiple semantic models, and a semantic model may cover a family of
operations or a region convention.

Examples:

```text
arith.addi:
  concrete execution model
  abstract integer/range model
  e-graph rewrite model
  backend lowering evidence model

func.func:
  callable-region operational model
  symbol-table model

builtin.module:
  top-level containment and symbol model
```

`execute` and `abstract` should not be hardcoded fields on one semantic record.
They are different semantic models or interpreters over the same syntax.

## Semantic Model Shape

IntelliC should treat semantics as programmable transition or interpretation
relations over syntax and trace state:

```text
SemanticModel
  name
  domain: operation family | dialect | region kind | pipeline stage
  relation: (Sy node, input facts, trace) -> (output facts, trace)
  applicability predicate
  evidence requirements
```

The trace is the general carrier. It can represent effects, obligations,
diagnostics, proof hints, abstract facts, execution events, backend evidence,
or LLM-agent review comments without forcing all of those into fixed fields.

```text
Trace
  ordered events
  fact tables
  evidence links
  diagnostics
  provenance
```

Specific projections such as "effects" or "obligations" can be derived from
trace events when needed. They should not be premature mandatory fields on
every semantic result.

## Trace-Updating Semantics

A semantic model should be able to define how trace changes:

```text
(op, inputs, trace_in) -> (outputs, trace_out)
```

or, more generally:

```text
(syntax, facts_in, trace_in) relation (facts_out, trace_out)
```

This leaves room for several styles:

- concrete operational semantics
- abstract interpretation
- trace semantics
- rule-based transition systems
- symbolic/e-graph semantics
- backend evidence semantics
- LLM-agent review actions that append trace evidence

The design should continue studying PL-style operational semantics and trace
semantics. The Fjfj paper is a useful reference because it avoids exponential
concurrent-method reasoning by restricting the language enough to characterize
modules one method/rule at a time, using partial transition relations and
tracked method-call structures. IntelliC should learn that lesson: semantic
modularity may require explicit restrictions and trace structure, not only more
metadata.

## Equality And E-Graphs

Do not put equivalence laws directly into every operation's semantic record as
the primary mechanism. IntelliC should absorb equality-saturation ideas from:

- egg: e-graphs, rewrites, analyses, extraction, cost functions, explanations.
- egglog: equality saturation combined with Datalog-style rules, relations,
  schedules, extraction, and incremental/composable analyses.
- xDSL eqsat support: creating e-classes in IR, applying PDL-derived rewrites
  non-destructively, adding costs, and extracting the chosen program.

IntelliC can expose an e-graph semantic/action model:

```text
IR fragment -> e-graph facts
rewrite/rule schedule -> saturated e-graph
cost model -> extracted IR fragment
trace -> rules applied, e-classes created, extraction choice
```

With this mechanism, operations do not need to each define their own
equivalence field. Equivalence is a separate semantic/action capability.

## Region Semantics

Do not invent placeholder project-specific dialect operations. Use MLIR/xDSL
dialect concepts such as `scf.if`, `cf.br`, `func.func`, and `builtin.module`
when examples need existing control-flow or containment operations.

Syntax holds regions. Semantic models define what a region means:

- `func.func` model: callable region and symbol behavior.
- `scf.if` model: chooses a region based on a condition and yields values.
- `cf` model: branch/control-flow transition behavior.
- `builtin.module` model: top-level containment and symbols.

IntelliC can copy and adjust xDSL/MLIR dialect syntax first, then add semantic
models gradually.

## Contracts

- An operation may have zero, one, or many semantic models.
- Missing semantics is allowed only when the current pipeline does not require
  semantics for that operation, or when an explicit opaque evidence boundary is
  present.
- Semantic applicability is checked by pipeline/action requirements, not by a
  global "one semantic def per op" rule.
- Trace is the common carrier for execution events, abstract facts, effects,
  obligations, diagnostics, proof hints, backend evidence, and LLM-agent notes.
- Specific concepts like effects or obligations should be trace projections
  unless a later design proves they need first-class dedicated storage.
- E-graph/equality reasoning is a semantic/action mechanism, not per-op
  equivalence fields.
- Semantic models must be inspectable and cite evidence requirements.

## Failure Modes

- A pipeline requires a semantic capability and no applicable model exists:
  semantic capability check fails.
- A semantic model updates trace in a shape the consumer cannot read: trace
  schema validation fails.
- A pass depends on an effect/obligation projection that no trace model
  provides: action planning fails before mutation.
- E-graph extraction changes syntax without extraction evidence: pipeline gate
  fails.
- Backend handoff sees opaque behavior without owner/evidence trace: handoff
  fails.

## Examples

### Example 1: Multiple Models For `arith.addi`

```text
syntax:
  %y = arith.addi %x, %c1 : i32

semantic models:
  concrete: (41, 1, trace) -> (42, trace + event)
  abstract: (range[0, 10], const[1], trace) -> (range[1, 11], trace + fact)
  eqsat: add e-node and rewrite facts into e-graph trace
```

Feature shown: one operation can participate in several semantic models.

Verification mapping: focused design evidence checks this example appears in
semantic execution, abstract interpretation, and e-graph action plans.

### Example 2: Trace Carries Effects Without Dedicated Effect Fields

```text
%token = async-like-op(...)
await-like-op(%token)
```

Trace sketch:

```text
event create_token token=%token owner=async-like-op
event consume_token token=%token owner=await-like-op
fact token_consumed(%token)
```

Feature shown: "obligation" is a trace convention. A gate can check the trace
for unconsumed tokens without every semantic result having an `obligations`
field.

Verification mapping: trace-schema evidence and a gate example that rejects a
missing `consume_token` event.

### Example 3: E-Graph Semantic Action

```egglog
(rewrite (Add a (Const 0)) a)
(rewrite (Mul a (Const 1)) a)
(run 4)
```

IntelliC action trace:

```text
event eclass_created value=%x
event rewrite_applied rule=add-zero
event extracted cost_model=ast-size
```

Feature shown: equality reasoning is an action/model over IR, not an
equivalence field on each operation.

Verification mapping: e-graph action evidence records e-class creation,
saturation, extraction, and selected replacement.

## Open Design Questions

- What is the minimal trace schema that can support concrete execution,
  abstract interpretation, e-graphs, backend evidence, and LLM-agent notes?
- Should semantic models be registered by operation class, dialect, region kind,
  or action capability?
- How much of xDSL's interpreter should be copied for the first concrete
  execution model?
- Which Fjfj-style restrictions are useful for making concurrent or effectful
  compiler semantics modular?
- Should e-graph integration start with xDSL's embedded eqsat dialect approach,
  egglog as an external engine, or a native IntelliC abstraction that can target
  either?

## Planned Verification Evidence

- Focused reread of the Fjfj paper notes before finalizing trace semantics.
- Focused source reading of egg, egglog, and xDSL eqsat before designing the
  first equality-saturation action.
- Example traces for concrete execution, abstract facts, token consumption, and
  e-graph extraction.
- Policy evidence that no design asserts one semantic definition per operation.

## Out Of Scope

- Full formal proof system in the first implementation.
- Selecting one final trace calculus before more examples are studied.
- Backend-specific semantic models beyond explicit opaque/evidence boundaries.
- Per-operation equivalence fields as the primary equivalence mechanism.
