# Design: Compiler Passes

> Review status: Draft only. Not reviewed or approved. This document records
> current working direction and fix advice for IntelliC; do not treat it as
> accepted architecture until explicit human review approves it.

## Goal

Define the mechanism for compiler work over `IR := Sy + Se`: analysis,
rewrite, transform, verification gates, semantic execution, equality
saturation, backend handoff, and LLM-agent participation.

The design should reduce artificial distinctions while still distinguishing
programmed compiler actions, agent-conducted actions, and agent-driven action
evolution.

## Decision

Use one general **compiler action** mechanism with two action kinds, plus a
separate agent-evolution workflow:

| Kind | Meaning | Typical Use |
| --- | --- | --- |
| `Fixed` | Programmed, deterministic compiler behavior | MLIR/xDSL-style passes, analyses, rewrites, gates, semantic execution |
| `AgentAct` | An LLM agent conducts a scoped action through compiler-provided APIs/hooks | Review evidence, query facts, propose diagnostics, propose mutation intents |

`AgentEvolve` is not a `CompilerAction` kind. It is a JIT-like evolution
workflow that generates, verifies, and registers a new `Fixed` action. After
registration, the generated action runs as an ordinary `Fixed` action.

A compiler action is:

```text
CompilerAction
  name
  kind: Fixed | AgentAct
  scope_kind
  match(scope, db) -> MatchSet records
  apply(scope, MatchSet, db) -> TraceDB records
  stages: optional ActionStage list
  evidence requirements
```

`required_facts` and `produced_facts` are not top-level action fields. They are
absorbed into the `match` and `apply` contracts: `match` declares and records
what it reads, and `apply` declares and records what it writes.

`apply` must not directly mutate `Sy`. It records facts, diagnostics, evidence,
and mutation intents in `TraceDB`. A separate stage, usually `MutatorStage`,
consumes recorded mutation intents and applies them through controlled syntax
mutation APIs. If a required-to-handle record remains pending at the end of the
action and attached stages, the action fails.

## Core Model

```text
ActionScope
  module | operation | region | block | dialect subset | e-graph | artifact

TraceDB
  one logical database per pipeline run
  ordered events
  typed fact/event relations
  projections over event/fact relations
  action transactions and checkpoints

MatchSet
  action_id
  matches: typed MatchRecord rows

ActionStage
  name
  consumes: relation keys
  produces: relation keys
  run(scope, db) -> db

AgentEvolutionJob
  hole: ActionHole | WeakActionCandidate
  constraints
  examples
  allowed_agent_apis
  evolve(...) -> FixedActionCandidate
  verify(candidate) -> CandidateVerification
  register(candidate) -> Fixed action version
```

Traditional concepts become special cases:

| Traditional Term | Unified Action View |
| --- | --- |
| Analysis | `Fixed` action whose match finds scopes and whose apply writes facts |
| Rewrite pattern | `Fixed` action whose apply records mutation intents, then `MutatorStage` applies them |
| Pass | Usually a broad `Fixed` action, possibly with several stages |
| Gate | `Fixed` action that fails if match/apply predicates are not satisfied |
| Semantic execution | `Fixed` action generated from selected `SemanticDef` records |
| Eqsat | `Fixed` action family over equivalence operations and extraction evidence |
| Agent review | `AgentAct` action that records review facts through agent APIs |
| Agent-assisted pass authoring | `AgentEvolutionJob` that produces a checked `Fixed` action candidate |

Effects, obligations, semantic-level facts, diagnostics, pass gates, agent
notes, and analysis results should be represented as `TraceDB` event/fact
relations or projections unless a later design proves a dedicated structure is
necessary.

## Match Records

`match` is not an unstructured boolean or hidden callback result. It produces
typed `MatchRecord` rows:

```text
MatchRecord
  action_id
  match_id
  scope
  subject
  bindings: typed tuple of syntax ids and fact ids
  read_set: relation/projection ids used by the matcher
  evidence
  status: matched | rejected
```

Examples:

```text
MatchRecord
  action=add-zero-canonicalize
  subject=%add
  bindings=(add=%add, lhs=%x, rhs=%zero, zero_fact=#fact42)
  read_set=(ConstValue, Uses)
  status=matched

MatchRecord
  action=backend-evidence-gate
  subject=%opaque
  bindings=(op=%opaque)
  read_set=(BackendOwner, EvidenceLink)
  status=rejected
```

The `read_set` replaces a separate `required_facts` field. Match evidence should
be enough for a human or LLM agent to understand why a scope was selected or
rejected.

## Apply And Stages

`apply` consumes match records and appends typed records to `TraceDB`. It may
write analysis facts, semantic execution facts, diagnostics, review notes, or
mutation intents. It does not directly edit `Sy`.

```text
apply add-zero-canonicalize:
  read MatchRecord(add=%add, lhs=%x, rhs=%zero)
  write MutationIntent.ReplaceUses(old=%add.result, new=%x)
  write RewriteEvidence(rule=add-zero, match_id=...)
```

Action stages run after `apply`:

```text
CompilerAction(add-zero-canonicalize)
  match
  apply
  stages:
    MutatorStage
    PendingRecordGate
```

`MutatorStage` is the only stage in the first design that mutates syntax. It
consumes `MutationIntent` records, applies controlled syntax edits, and writes
one of:

```text
MutationApplied(intent_id, changed_syntax, evidence)
MutationRejected(intent_id, reason, evidence)
```

`PendingRecordGate` checks that required-to-handle records have been consumed or
rejected. For example, a pending `MutationIntent` left after an action means the
action failed, even if match/apply returned normally.

## Pipeline TraceDB Management

A pipeline run has one authoritative pipeline `TraceDB`. The pipeline does not
create a fresh shared semantic database for each pass. Instead it uses action
ids, stage ids, scopes, transactions, and checkpoints inside the same database.

```text
PipelineRun
  input IR
  pipeline_db: TraceDB
  actions:
    ActionFrame(action_id=1, transaction=t1)
    ActionFrame(action_id=2, transaction=t2)
    ...
  checkpoints:
    before-canonicalize
    after-canonicalize
    before-backend
```

Management rules:

- Each action runs in an action transaction or frame.
- Successful actions commit their shared records into the pipeline `TraceDB`.
- Failed actions keep failure evidence; their staged syntax mutations are not
  committed unless an explicit recovery policy says otherwise.
- Before/after comparisons use checkpoints or projection labels in the same
  `TraceDB`, not unrelated databases.
- Speculative `AgentAct` work may use a branch or overlay database, but merging
  it back requires explicit accepted records, usually accepted `MutationIntent`
  or review facts.
- Semantic execution actions write execution or abstract facts under a run id,
  level selection, action id, and scope, so several executions can coexist in
  the same pipeline database.

This gives one audit trail for the pipeline while still allowing scoped
transactions, snapshots, and speculative agent work.

The pipeline `TraceDB` does play some roles similar to a classic analysis-cache
system: it stores cross-action derived facts, lets later actions reuse them, and
supports invalidation through retraction/supersession. But it is broader than a
cache because it is also the pipeline's evidence, replay, and gate substrate.

## Action-Owned Auxiliary TraceDBs

Actions may also create auxiliary `TraceDB` instances for local computation.
These are action-owned databases, not the authoritative pipeline database.

Typical uses:

- temporary analysis workspaces
- solver/search state
- action-private materializations
- speculative local reasoning before exporting accepted results
- local cache shapes tuned to one action algorithm

Shape:

```text
ActionFrame
  pipeline_db: authoritative shared TraceDB
  auxiliary_dbs:
    local_analysis_db?
    speculative_db?
    cost_model_db?
```

Contracts:

- An auxiliary `TraceDB` is owned by one action frame unless the pipeline
  explicitly declares a longer-lived shared service database.
- Auxiliary databases may have different indexes, projections, or temporary
  schemas optimized for that action.
- Auxiliary records do not affect pipeline gates, replay, or later actions until
  the action exports selected facts/events/evidence into the pipeline `TraceDB`.
- Export is explicit and typed: the action writes canonical `TraceRecord`
  entries or projection materializations into the pipeline database.
- The pipeline must be reproducible from the pipeline `TraceDB` plus declared
  artifacts. An auxiliary database may be discarded after action completion
  unless retained as an artifact.

Minimal export shapes:

```text
ExportFact(relation, subject, key, value, provenance)
ExportProjection(name, rows, provenance)
ExportEvidenceLink(subject, artifact_ref, provenance)
```

## TraceDB Indexing For Actions

The first slice should not introduce a separate pipeline-level analysis-cache
subsystem. Fast shared lookup stays inside the authoritative pipeline `TraceDB`
through typed relation indexes and materialized projections. Individual actions
may still keep auxiliary `TraceDB`s for local algorithms.

Base indexes come from the semantics design:

- `(relation, subject, validity)`
- `(relation, key, validity)`
- `(relation, scope, validity)`
- `(relation, owner, validity)`
- `(relation, order)`
- `(record_id)`

Compiler actions add only two further indexing rules:

- `provenance.action_id` or frame id must be indexable so the pipeline can ask
  which action produced or retracted a record.
- Expensive named projections may be materialized and checkpointed inside the
  same `TraceDB`; they are not a separate cache layer.

Minimal first-slice materializations:

```text
CurrentBySubject(relation, subject) -> live records
CurrentByScope(relation, scope) -> live records
CurrentByKey(relation, key) -> live records
ProducedByAction(action_id, relation) -> records
CheckpointProjection(checkpoint, projection_name) -> materialized rows
```

Index/materialization policy:

- `RelationSchema` may declare index hints for hot relations in either the
  pipeline `TraceDB` or an auxiliary action-owned `TraceDB`.
- `ProjectionSpec` may declare whether a projection is computed on demand or
  materialized at checkpoints.
- Matchers and gates query the pipeline `TraceDB`; they do not depend on private
  side caches that bypass replay or evidence.
- If later performance work needs more indexes, add them as `TraceDB`
  declarations or projection materializations for the authoritative pipeline
  database. Local action caches remain allowed as auxiliary databases.

## Semantic Execution In The Pipeline

Semantic execution should be a first-class `Fixed` action type. It can run:

- before a transform to capture baseline behavior
- after a transform to compare `TraceDB` projections
- inside a pass to produce abstract facts
- as a gate before backend handoff
- as evidence for LLM-agent review

Semantic execution actions request semantic definitions from the registry by
typed owner and level selection, such as `ArithAddiOp` at `ConcreteValue` or at
the allowed set `{ConcreteValue, AbstractRange}`. They should not dispatch
through one hardcoded operation semantics field. If a selected level set matches
more than one definition for the same owner, the action must provide a typed
resolution policy or fail before mutation intents are emitted.

Pipeline example:

```text
parse-ir
structural-verify
execute-example-db[action_id=3, run=before]
canonicalize-with-egraph[action_id=4, stages=MutatorStage, PendingRecordGate]
execute-example-db[action_id=5, run=after]
compare-db-projection
agent-review-evidence
backend-evidence-gate
emit-artifact
```

This makes execution and LLM-agent participation central, not afterthoughts.

## LLM-Agent Participation

LLM agents participate through two different mechanisms:

- `AgentEvolve`: a JIT-like workflow that produces a verified `Fixed` action.
- `AgentAct`: a real `CompilerAction` whose match/apply are conducted by an
  agent through compiler-provided APIs.

Neither mechanism may mutate syntax through unrecorded side effects.

### AgentEvolve

`AgentEvolve` is not a compiler action. It is an action-generation workflow:

```text
AgentEvolutionJob
  input:
    ActionHole(kind=rewrite | analysis | gate | execution)
    examples
    semantic contracts
    allowed agent APIs
    verification requirements
  output:
    FixedActionCandidate(match_spec, apply_spec, stages)
    VerificationPlan
    AgentRationale
    CandidateVerification
```

JIT-like flow:

1. The compiler records an `ActionHole` or weak `FixedActionCandidate`.
2. The agent uses allowed read/query APIs to synthesize a `FixedActionCandidate`.
3. The candidate is instantiated in a sandbox action registry.
4. Verification runs examples, schema checks, match/apply contract checks,
   pending-record checks, and any domain-specific gates.
5. If verification passes, the candidate is registered as a versioned `Fixed`
   action.
6. Later pipelines run that registered action as `kind=Fixed`.

The result is not trusted merely because an agent produced it. The generated
action must pass review and verification before registration.

### AgentAct

`AgentAct` lets an agent conduct a scoped action directly:

```text
AgentActAction
  kind: AgentAct
  match:
    agent runtime may call agent APIs to inspect scope and query evidence
    agent emits MatchRecord rows through typed APIs
  apply:
    agent runtime may call agent APIs to write review facts, diagnostics, and
    mutation intents
  stages:
    HumanOrPolicyGate
    optional MutatorStage
    PendingRecordGate
```

Agent-facing compiler APIs should be typed and policy-checked:

```text
AgentCompilerAPI
  inspect_ir(scope) -> scoped syntax view
  query_db(projection, filters) -> typed facts/events
  request_semantic_execution(scope, level_selection) -> run id or rejected
  emit_match(bindings, evidence) -> MatchRecord
  write_review(subject, risk, notes, evidence) -> AgentReview
  write_diagnostic(subject, message, severity, evidence) -> DiagnosticSuggestion
  propose_mutation(intent, evidence) -> MutationIntent
  request_gate(gate_name, scope) -> gate result
```

These APIs are not direct object mutation APIs. They append typed records to
`TraceDB` or request controlled compiler services. Default automated policy:
`AgentAct` may write review, diagnostic, and proposal facts, but may not commit
syntax mutation unless a policy gate and mutator stage are attached.

## Cross-Language Action Host ABI

Python actions and future C++ actions should share one language-neutral action
host contract. They should not share Python objects, C++ pointers, or ad hoc
dict payloads across the boundary.

Shared boundary:

```text
ActionHostAPI
  begin_frame(action, scope, options) -> FrameHandle
  inspect_syntax(refs) -> SyntaxView rows
  query_relations(read_spec) -> RecordCursor
  query_projection(name, filters) -> ProjectionCursor
  append_match(MatchRecordWire) -> match id
  append_record(TraceRecordWire) -> record id
  attach_evidence(EvidenceEnvelope) -> EvidenceRef
  commit_frame(handle)
  rollback_frame(handle, reason)
```

Canonical interchange rules:

- Syntax crosses the boundary through stable syntax ids/refs, not raw language
  object pointers.
- `TraceDB` rows cross the boundary through the canonical `TraceRecord`,
  `RelationSchema`, and `ProjectionSpec` schemas.
- Relation key/value payloads use relation-owned typed codecs so Python and C++
  validate the same fact/event shape.
- Evidence is referenced by `EvidenceRef`; large blobs live in an artifact
  store, while `TraceDB` keeps typed manifests and links.
- In-memory wrappers may differ by language, but the storage/wire contract is
  identical.

This keeps replay, evidence inspection, and mixed-language pipelines coherent:
a Python action and a C++ action should produce the same `MatchRecord`,
`TraceRecord`, and evidence shapes for the same compiler effect.

## E-Graph Operation Actions

Equality saturation should be represented as an action family:

```text
build-egraph:
  IR fragment -> explicit equivalence/e-class operations

saturate:
  ruleset + e-graph operations -> expanded e-graph operations plus facts/events

extract:
  cost model + e-graph operations -> selected IR fragment + extraction evidence
  optional MutatorStage consumes extraction MutationIntent
```

xDSL's eqsat flow is a useful starting point: create e-class ops, apply
rewrites non-destructively, add costs, and extract. egg and egglog show broader
models for rewrite saturation, analyses, cost functions, Datalog-style rules,
and extraction. This is an IR/action mechanism, not a semantic-definition level.

## TraceDB-Based Gates

Gates are actions that validate semantic database and syntax predicates:

```text
structural_gate:
  fail if structural diagnostics exist

semantic_gate:
  fail if selected semantic facts are absent or contradictory

backend_gate:
  fail if opaque semantic owner/evidence facts are missing

agent_gate:
  fail if required review facts or explicit waivers are absent

pending_record_gate:
  fail if required-to-handle records remain pending
```

No separate gate subsystem is needed unless implementation proves otherwise.

## Contracts

- All pipeline work runs as `CompilerAction`, attached `ActionStage`, or an
  explicit non-action `AgentEvolutionJob`.
- Every compiler action has kind `Fixed` or `AgentAct`.
- `AgentEvolve` is a non-action JIT-like workflow that generates a verified,
  versioned `Fixed` action candidate.
- `match` writes typed `MatchRecord` rows; match reads are captured in those
  records instead of a separate `required_facts` action field.
- `apply` writes typed `TraceDB` records; apply writes replace a separate
  `produced_facts` action field.
- `apply` must not directly mutate `Sy`.
- Syntax mutation is performed by `MutatorStage` consuming recorded
  `MutationIntent` records.
- Required-to-handle records such as mutation intents must be consumed,
  rejected, or explicitly waived before the action succeeds.
- A pipeline has one authoritative shared `TraceDB` per run, with action
  frames, transactions, checkpoints, and optional speculative overlays.
- Actions may create auxiliary `TraceDB` instances for local computation, but
  only records exported into the pipeline `TraceDB` participate in pipeline
  gates, replay, or cross-action reuse.
- Semantic execution facts from multiple runs coexist in the same pipeline
  database under action/run/scope/level labels.
- The pipeline `TraceDB` partly subsumes classic cross-action analysis-cache
  roles, but it is broader because it also carries evidence, history, and gate
  inputs.
- Fast shared lookup stays inside the pipeline `TraceDB` through declared
  relation indexes and optional materialized projections, not through a separate
  pipeline-level analysis-cache subsystem.
- `AgentAct` must interact with compiler infrastructure only through typed,
  policy-checked agent APIs.
- Agent-produced behavior must be evidence-backed and policy-gated before it can
  mutate syntax or become a registered `Fixed` action.
- Python and future C++ actions must share the same language-neutral
  `ActionHostAPI`, `TraceRecord` schema, relation codecs, and evidence-ref
  contract.
- A pipeline is reproducible from its action list, action kinds, registered
  fixed-action versions, options, input evidence, committed `TraceDB`, and
  checkpoint labels.

## Failure Modes

- `match` selects a scope but writes no `MatchRecord`: action validation fails.
- `apply` reads syntax or facts not cited by match evidence or its declared
  apply contract: action validation fails.
- `apply` mutates syntax directly: action validation fails.
- `MutationIntent` remains pending after all attached stages: action fails.
- `MutatorStage` cannot apply or reject a mutation intent: action fails.
- `AgentEvolve` is scheduled as a `CompilerAction`: pipeline validation fails.
- `AgentEvolutionJob` emits a fixed-action candidate without verification
  evidence: candidate registration fails.
- `AgentAct` lacks required scoped evidence, sandbox policy, or review gate:
  action is skipped or fails according to pipeline policy.
- `AgentAct` tries to access compiler internals outside the typed agent API:
  action validation fails.
- A pipeline gate or later action depends on an auxiliary action-local database
  record that was never exported into the pipeline `TraceDB`: validation fails.
- Semantic execution writes facts without action/run/scope/level labels:
  projection validation fails.
- A speculative agent overlay is merged without accepted records: merge fails.
- A Python or C++ action emits a record or evidence payload that does not
  validate against the canonical schema/codec: frame commit fails.
- E-graph extraction lacks cost/evidence facts or an extraction mutation intent:
  extraction gate fails.
- Backend handoff sees opaque semantics without owner/evidence facts: handoff
  fails.

## Examples

### Example 1: Rewrite As Fixed Action

```text
action add-zero-canonicalize kind=Fixed
  match:
    find arith.addi(%x, %zero)
    read ConstValue(%zero, 0)
    write MatchRecord(match_id=m1, bindings=(add=%add, lhs=%x, rhs=%zero))

  apply:
    write MutationIntent.ReplaceUses(intent=i1, old=%add.result, new=%x)
    write RewriteEvidence(rule=add-zero, match=m1)

  stages:
    MutatorStage consumes i1 -> MutationApplied(i1)
    PendingRecordGate verifies no pending MutationIntent
```

Feature shown: rewrite actions record a mutation intent; mutation happens only
in the mutator stage.

Verification mapping: evidence checks match record, mutation intent,
mutation-applied record, and absence of pending intents.

### Example 2: Analysis As Fixed Action

```text
action infer-const-zero kind=Fixed
  match:
    find arith.constant 0 : i32
    write MatchRecord(match_id=m1, bindings=(constant=%c0))

  apply:
    write ConstValue(subject=%c0, value=0)
```

Feature shown: analysis is an action that produces `TraceDB` facts rather than
a separate subsystem with unrelated cache rules.

Verification mapping: pipeline evidence shows `add-zero-canonicalize` depends
on a fact produced by `infer-const-zero`.

### Example 3: AgentEvolve Generates A Fixed Action

```text
AgentEvolutionJob:
  input:
    ActionHole(kind=rewrite, pattern="arith.muli x 1")
    examples:
      arith.muli(%x, %one) -> %x
    allowed APIs:
      inspect_ir, query_db, emit FixedActionCandidate

  evolve:
    write FixedActionCandidate(name=mul-one-canonicalize)
    write VerificationPlan(example="muli(x, 1) -> x")
    write AgentRationale(...)

  verify:
    run examples
    check match/apply schemas
    check pending-record behavior

  register:
    FixedAction(name=mul-one-canonicalize, version=v1)
```

Feature shown: `AgentEvolve` is a JIT-like generation workflow, not a
`CompilerAction`. Its output is a versioned `Fixed` action.

Verification mapping: candidate evidence includes the generated action spec,
review decision, example replay, and registered fixed-action version.

### Example 4: AgentAct Review With Optional Mutation

```text
action agent-review-before-backend kind=AgentAct
  match:
    api.inspect_ir(@m)
    api.query_db(before_after_projection, scope=@m)
    api.query_db(backend_evidence, scope=@m)
    api.emit_match(bindings=(module=@m, diff=#d), evidence=...)

  apply:
    api.write_review(subject=@m, risk=medium, notes=[...])
    api.write_diagnostic(subject=%op, message=..., severity=warning)
    optionally api.propose_mutation(MutationIntent.ReplaceUses(...))

  stages:
    HumanOrPolicyGate
    optional MutatorStage
    PendingRecordGate
```

Feature shown: an agent can conduct an action directly, but syntax mutation is
still recorded through agent APIs as intent and gated before a mutator stage
applies it.

Verification mapping: handoff notes include review facts, policy-gate outcome,
and no pending required records.

### Example 5: Pipeline TraceDB Lifecycle

```text
pipeline run #17:
  db = TraceDB(run=17)
  checkpoint before-canonicalize
  action infer-const-zero action_id=1 commits ConstValue facts
  action add-zero-canonicalize action_id=2 commits MatchRecord, MutationIntent,
         MutationApplied, RewriteEvidence
  checkpoint after-canonicalize
  action execute-example-db action_id=3 run=after commits ConcreteValue facts
  action compare-db-projection action_id=4 reads before/after checkpoints
```

Feature shown: the pipeline has one authoritative shared `TraceDB`. Action
frames and checkpoints separate shared evidence, while auxiliary action-local
databases remain optional.

Verification mapping: replay evidence reconstructs action order, committed
records, checkpoint projections, and final IR.

### Example 6: Action Uses Auxiliary TraceDB Then Exports

```text
action infer-loop-invariants kind=Fixed
  create auxiliary_db=LoopInvariantWorkspace

  match:
    read loop scopes from pipeline_db

  apply:
    compute candidate invariants in auxiliary_db
    export InvariantFact(subject=%loop, value=...)
    export EvidenceLink(subject=%loop, artifact=aux://loop-proof-17)

  stages:
    PendingRecordGate
```

Feature shown: an action may use its own `TraceDB`-like workspace, but only the
explicitly exported facts/evidence become part of the pipeline record.

## Planned Verification Evidence

- Pipeline sketches showing `Fixed` actions, `AgentAct` actions, and
  `AgentEvolutionJob` workflows that generate fixed actions.
- Match-record evidence for analysis, rewrite, gate, semantic execution, eqsat,
  and agent actions.
- Example `TraceDB` update sequence for an add-zero canonicalization pipeline
  with `MutationIntent` and `MutatorStage`.
- Example `TraceDB` lifecycle with action frames, checkpoints, and one logical
  pipeline database.
- Example relation/projection indexing evidence showing hot lookups served by
  pipeline `TraceDB` materializations rather than a separate pipeline-level
  analysis cache.
- Example action-local auxiliary `TraceDB` evidence showing explicit export into
  the authoritative pipeline database.
- Negative evidence where an unconsumed mutation intent causes action failure.
- Example `AgentEvolve` JIT-like candidate registration flow.
- Example `AgentAct` review flow through typed agent APIs, with mutation blocked
  unless policy-gated.
- Mixed-language evidence where a Python action and a future C++ action emit the
  same canonical `MatchRecord`, `TraceRecord`, and evidence-reference shapes.

## Out Of Scope

- Production optimization suite.
- Backend-specific lowering details.
- Distributed pass execution.
- Full proof automation.
- Granting LLM agents direct unrecorded mutation authority.
