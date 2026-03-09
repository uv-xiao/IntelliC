# Feature: Agentic-LLM-Friendly Compiler Development

## Goal

Make HTP a framework where **fully autonomous** LLM agents can:

1) understand compiler behavior and failures from artifacts alone,
2) propose and apply changes through **bounded, typed extension surfaces**,
3) verify correctness/performance via standardized gates,
4) leave durable provenance that keeps the project healthy long-term.

This feature is *not* “LLMs write random code”. It is: the framework is designed so agent work is **contracted,
reproducible, and reviewable**, instead of being driven by pass-order folklore and implicit invariants.

Design stance:

> LLM-based development is a native target for HTP’s architecture.

This means the framework’s core contracts (IR staging, diagnostics, artifact schemas, pass contracts) are designed to be
machine-consumable by default, not retrofitted.

## What “agent-friendliness” means in HTP (operational)

HTP is agent-friendly if the following are true:

- **Contracts are first-class**: a change can be expressed as a modification to a pass/pipeline/intrinsic/backend that has
  an explicit `requires/provides/invalidates` contract, plus typed layout/effect rules.
- **State is serializable**: the compiler can emit stable dumps of “what the program is” at key boundaries (AST + typed
  metadata, capability set, effect obligations, layout facets).
- **Failures are localized**: diagnostics point to a contract boundary (missing capability, effect mismatch, layout
  illegality, missing backend handler) with a stable error code.
- **Repro is automatic**: the artifact package contains everything needed to replay compilation and to reproduce a
  failure/regression.
- **Replay is verifiable**: stage programs are runnable in `mode="sim"` so agents can test intermediate behavior and
  localize regressions without relying on internal compiler state.
- **Edits are bounded**: there are “safe corridors” (templates) for adding intrinsics, passes, pipeline steps, and backend
  handlers, so an agent changes one surface at a time.

These requirements align directly with existing HTP principles:
- capability-typed composition (`docs/todo/feats/01_extensibility.md`)
- pass tracing and dumps (`docs/todo/feats/09_debuggability.md`)
- artifact-first manifests (`docs/design/impls/04_artifact_manifest.md`)

## Design requirements (language/framework level)

### 1) Stable identities and “semantic diffs”

Agents debug by comparing states. HTP should support:

- stage-local `node_id` for deterministic blame within a stage,
- cross-stage identities:
  - `entity_id` for constructs/statements,
  - `binding_id` for variables/bindings (handles shadowing/renaming),
- and explicit mapping files for major rewrites (`maps/entity_map.json`, `maps/binding_map.json`),
- plus “semantic diff” tooling (what changed in capabilities/effects/layout between pass A and pass B).

This turns “mysterious regressions” into structured deltas the agent can search over.

#### 1.1 Replay as a first-class oracle

Semantic diffs are strongest when they are backed by execution:

- structured stage dumps provide “what changed”
- `ir/stages/<id>/program.py` replay in `mode="sim"` provides “did behavior change”

Together, they enable automated stage bisect and minimize guesswork in autonomous loops.

#### 1.2 Identity and mapping are the foundation for analysis reuse

Agents (and compiler passes) need to refer to “the same construct” across transformations:

- “this loop is the pipelined k-loop”
- “this variable is the ping-pong slot index”

HTP therefore needs stable identities for:

- constructs/statements (`entity_id`)
- variables (`binding_id`, disambiguates shadowing)

and explicit mapping files for major rewrites (`entity_map.json`, `binding_map.json`) so agents can track changes without
heuristic AST matching.

Deep dive: `docs/design/impls/01_ir_model.md`.

### 2) Typed effects and protocol obligations

Autonomous agents must not “accidentally” create deadlocks or invalid async pipelines.

HTP should represent async/protocol constructs (channels, buffered handoffs, barriers/events, collectives) as **typed
effects** with checkable obligations, so:

- legality is verified early,
- failures are diagnosable (“missing discharge”, “protocol mismatch”, “capacity violation”),
- backends can provide alternate lowerings when capabilities differ.

### 3) Pass/pipeline contracts as machine-checkable metadata

Each pass and pipeline must declare:

- `requires/provides/invalidates` capabilities
- versioned parameters and defaults
- invariants it enforces
- invariants it assumes

This enables:

- a solver to construct legal pipelines,
- and an agent to automatically place new passes in the correct phase or be told precisely why it cannot.

### 4) Artifact packages as “context packs”

For autonomy, “context” must not be an ad-hoc pile of logs. Each compile emits:

- `manifest.json` (pipeline, versions, target, capabilities)
- `ir/pass_trace.jsonl` (timings, before/after dump pointers, diagnostics)
- IR dumps for key boundaries (AST + typed metadata snapshots)

These are sufficient inputs for an agent loop.

In HTP, the artifact package is also a **training/evaluation substrate**:

- failures are encoded as structured diagnostics + evidence pointers,
- “fixes” can be evaluated by replaying stages and comparing golden artifacts,
- and long-horizon health can be monitored by regression suites over packages.

### 5) Extension templates (safe corridors)

HTP should ship templates/recipes for:

- adding an intrinsic with a typed contract and stub backend handlers
- adding a pass with contract + tracing hooks
- adding a backend handler (lowering/emitter) behind capability gates
- adding a pipeline variant (with explicit output artifact contract)

The objective is to make “agent edits” predictable, testable, and constrained.

## Non-negotiable agent-native contracts (short list)

If HTP is a native target for autonomous development, these must be treated as architecture constraints:

- stage replay always exists in `sim` (`program.py` never disappears)
- diagnostics are stable-coded + machine-localizing
- analyses are staged and versioned (no hidden caches for important facts)
- manifests record provenance for autonomous edits (`extensions.agent.*`)

## Why this is better (agentically) than typical MLIR-first infrastructures

MLIR provides mechanisms (dialects/passes/patterns), but many real systems end up with:

- implicit invariants encoded as attrs and pass ordering,
- target-specific branching in pipeline construction,
- diagnostics that are human-oriented but not machine-localizing,
- limited “artifact-only replay” capability.

HTP’s bet is: if contracts + artifacts + effect/layout typing are the primary interface, then autonomy becomes feasible and
healthy.

Concrete evidence from existing systems (code-grounded):
- Triton’s warp specialization shows “attrs as APIs” and phase-coupled pipelines that are correct but non-obvious to extend
  safely; see `docs/todo/reports/retargetable_extensibility_report.md`.
- TileLang’s high-end instruction selection (e.g., TMA/Bulk/LDSM/TMEM) is explicitly target-conditional, and contains
  backend-specific escape hatches; see the same report plus its code pointers.

## “Fully autonomous” requires provenance, not just logs

To keep the project healthy, HTP should treat agent activity as part of the artifact contract:

- policy (what edits are permitted, what gates are required)
- structured provenance (what changed, why, what evidence, what gates passed)

Recommended location: manifest extension namespace, e.g. `extensions.agent.*` (see `docs/design/impls/10_agentic_tooling.md`).

## Relationship to the built-in agent loop

This feature defines the **design constraints** that make a built-in agent loop possible. The loop itself is specified in:
- `docs/design/impls/10_agentic_tooling.md`
