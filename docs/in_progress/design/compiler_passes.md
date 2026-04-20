# Design: Compiler Passes

> Review status: Draft only. Not reviewed or approved. This document records
> current working direction and fix advice for IntelliC; do not treat it as
> accepted architecture until explicit human review approves it.

## Goal

Define the mechanism for compiler work over `IR := Sy + Se`: analysis,
rewrite, transform, verification gates, semantic execution, equality
saturation, backend handoff, and LLM-agent participation.

The design should reduce artificial distinctions. Passes, analyses, rewrites,
and gates should share as much infrastructure as possible.

## Decision

Use one general **compiler action** mechanism.

```text
CompilerAction
  name
  match(scope, trace) -> matches
  apply(scope, matches, trace) -> updated scope, updated trace
  evidence requirements
```

Traditional concepts become special cases:

| Traditional Term | Unified Action View |
| --- | --- |
| Analysis | Match a scope, compute facts, append trace/fact-table entries |
| Rewrite pattern | Match local syntax/facts, mutate through rewriter, append evidence |
| Pass | Broader action whose matcher is often simple and whose applier may run arbitrary Python/C++ logic |
| Gate | Action that matches required facts and fails if predicates are absent |
| Semantic execution | Action that interprets syntax and appends execution trace/facts |
| Eqsat | Action that builds/saturates/extracts an e-graph and records evidence |
| LLM-agent step | Action that reads scoped evidence and appends review/proposal trace |

This unification should make implementation easier and architecture more
consistent.

## Core Model

```text
ActionScope
  module | operation | region | block | dialect subset | e-graph | artifact

ActionTrace
  ordered events
  fact tables
  diagnostics
  evidence links
  provenance
  agent notes

CompilerAction
  name
  scope_kind
  required_facts
  produced_facts
  match(scope, trace)
  apply(scope, matches, trace)
```

Effects, obligations, semantic capabilities, diagnostics, pass gates, and
analysis results should be represented as trace events or facts unless a later
design proves a dedicated structure is necessary.

## Match And Apply

The common shape is:

```text
match:
  inspect syntax, semantic models, trace facts, and optional external evidence

apply:
  update syntax through controlled mutation APIs
  update trace with produced facts/events/evidence
  emit diagnostics or failure
```

A pass is just a flexible action with a broad matcher and a general applier.
A rewrite pattern is a narrow action. An analysis is an action that usually
does not mutate syntax. A gate is an action that fails instead of producing a
normal transformed scope.

## Semantic Execution In The Pipeline

Semantic execution should be a first-class action type. It can run:

- before a transform to capture baseline behavior
- after a transform to compare traces
- inside a pass to produce abstract facts
- as a gate before backend handoff
- as evidence for LLM-agent review

Pipeline example:

```text
parse-ir
structural-verify
execute-example-trace
canonicalize-with-egraph
execute-example-trace
compare-trace-projection
llm-review-evidence
backend-evidence-gate
emit-artifact
```

This makes execution and LLM-agent participation central, not afterthoughts.

## LLM-Agent Actions

LLM agents can participate as scoped actions when the pipeline has enough
evidence:

```text
LLMReviewAction
  match: changed IR plus before/after traces exist
  apply: append review facts, risk notes, suggested checks
```

Agent actions must not mutate compiler IR directly in automated pipelines
unless explicitly allowed by a task. Their default role is evidence review,
proposal generation, and diagnostics explanation.

## E-Graph Actions

Equality saturation should be represented as an action family:

```text
build-egraph:
  IR fragment -> e-classes/e-nodes trace

saturate:
  ruleset + e-graph -> expanded e-graph trace

extract:
  cost model + e-graph -> selected IR fragment + extraction evidence
```

xDSL's eqsat flow is a useful starting point: create e-class ops, apply
rewrites non-destructively, add costs, and extract. egg and egglog show broader
models for rewrite saturation, analyses, cost functions, Datalog-style rules,
and extraction.

## Trace-Based Gates

Gates are actions that validate trace and syntax predicates:

```text
structural_gate:
  requires no broken parent/use/type facts

semantic_gate:
  requires semantic capability facts for selected scope

backend_gate:
  requires opaque semantic owner and evidence facts

agent_gate:
  requires review trace or explicitly waived review
```

No separate gate subsystem is needed unless implementation proves otherwise.

## Contracts

- All pipeline work runs as `CompilerAction` or a composition of actions.
- Actions declare required and produced trace facts.
- Actions mutate syntax only through controlled mutation APIs.
- Analyses, rewrites, passes, gates, semantic execution, eqsat, and LLM-agent
  steps share trace and evidence infrastructure.
- Action traces are stable enough for human/agent review.
- A pipeline is reproducible from its action list, options, and input evidence.
- Documentation-only design changes do not need automated tests, but they still
  need focused reread or policy evidence.

## Failure Modes

- Action requires facts that no prior action produced: planning fails.
- Action mutates syntax without trace update: debug gate fails.
- Gate predicate fails: pipeline stops with diagnostics.
- LLM-agent action lacks required scoped evidence: action is skipped or fails
  according to pipeline policy.
- E-graph extraction lacks cost/evidence trace: extraction gate fails.
- Backend handoff sees opaque semantics without evidence facts: handoff fails.

## Examples

### Example 1: Rewrite As Action

```text
action add-zero-canonicalize
  match: arith.addi(%x, %zero) and fact const_zero(%zero)
  apply: replace add result uses with %x
  trace: event rewrite_applied rule=add-zero
```

Feature shown: rewrite patterns are narrow compiler actions.

Verification mapping: focused design evidence checks matcher, applier, and
trace event are all specified.

### Example 2: Analysis As Action

```text
action infer-const-zero
  match: arith.constant 0 : i32
  apply: append fact const_zero(%c0)
```

Feature shown: analysis is an action that produces trace facts rather than a
separate subsystem with unrelated cache rules.

Verification mapping: pipeline evidence shows `add-zero-canonicalize` depends
on a fact produced by `infer-const-zero`.

### Example 3: Gate As Action

```text
action backend-evidence-gate
  match: all opaque backend operations
  apply: fail if semantic_owner/evidence facts are missing
```

Feature shown: gates are validation actions over syntax and trace.

Verification mapping: negative evidence example stops before emission; positive
example records owner/evidence facts and proceeds.

### Example 4: LLM-Agent Pipeline Action

```text
action llm-review-before-backend
  match: changed IR, before/after trace, backend evidence
  apply: append agent_review risk=low notes=[...]
```

Feature shown: LLM agents can be part of the pass pipeline as evidence
producers or reviewers without receiving unchecked mutation authority.

Verification mapping: handoff notes include the agent review trace or an
explicit waiver.

## Open Design Questions

- What is the minimal trace schema shared by all action kinds?
- How should action facts be indexed for fast lookup without rebuilding a
  separate analysis-cache subsystem too early?
- Which actions may mutate syntax in automated mode?
- How should Python actions and future C++ actions share trace/evidence format?
- How should LLM-agent actions be sandboxed and made reproducible enough for
  compiler engineering workflows?

## Planned Verification Evidence

- Pipeline sketches showing analysis, rewrite, gate, semantic execution, eqsat,
  and LLM-agent review as the same action shape.
- Focused reread comparing xDSL pass/rewriter/eqsat flow to the unified action
  model.
- Example trace for an add-zero canonicalization pipeline.
- Example trace for backend evidence gate.

## Out Of Scope

- Production optimization suite.
- Backend-specific lowering details.
- Distributed pass execution.
- Full proof automation.
