# IntelliC

IntelliC is an intelligent compiler infrastructure for both human programmers
and LLM agents.

Its goal is not only to represent programs, but to make compiler structure,
meaning, evidence, and transformation workflows inspectable enough that humans
and agents can read, explain, verify, and extend the same system.

Use `intellic` for the package name. Use `ic` only as a short local
abbreviation where brevity matters.

## Why IntelliC

The clean rebuild starts from one constraint: major compiler representations
should be understandable and verifiable before they become implementation
dependencies.

That drives the project toward:

- a readable IR model
- explicit semantics, not syntax-only infrastructure
- evidence-bearing compiler actions and pipelines
- programming surfaces that feel native in Python without depending on a custom
  parser stack

## High-Level Architecture

IntelliC's accepted architecture is:

```text
Lang := Surface | IR
Surface := IR + Construction API
IR := Sy + Se
```

Practical meaning:

- `Surface` is what humans and LLM agents program.
- `IR` is what the compiler reasons about.
- `Sy` is syntax: operations, regions, blocks, values, types, attributes,
  verification, and canonical IR text.
- `Se` is semantics: what operations mean, how they execute or abstract, and
  what facts/events/evidence they produce.

## Core Design

### Syntax (`Sy`)

IntelliC adopts an MLIR/xDSL-derived syntax model.

- canonical IR syntax follows MLIR/xDSL structure
- the strict `ir_parser` is for canonical IR text
- the public infrastructure is native IntelliC code, not wrapper imports around
  xDSL

### Surface Construction

IntelliC does not center Python authoring on parser-level composition.

Instead, surfaces are built through Python-native construction APIs:

- builders
- decorators
- operator hooks
- region helpers

The accepted direction is `Surface := IR + Construction API`, not `Surface :=
IR + Parser`.

### Semantics (`Se`)

IntelliC treats semantics as a first-class part of IR, not as an afterthought.

- operations and dialects contribute thin typed `SemanticDef` records
- semantic levels are extensible rather than fixed to one enum
- semantics run over a shared `TraceDB` of facts and events
- control flow, abstract interpretation, backend evidence, and replay all live
  in that semantic architecture

### Compiler Actions And Pipelines

Compiler work is unified around one action mechanism.

- `Fixed` actions cover programmed compiler behavior such as analysis, rewrite,
  gates, and semantic execution
- `AgentAct` lets an LLM agent conduct a scoped action through typed compiler
  APIs
- `AgentEvolve` is separate from runtime action execution; it generates checked
  `Fixed` actions
- syntax mutation is recorded as intent in `TraceDB` and applied through
  explicit mutator stages

Pipelines use one authoritative shared `TraceDB` per run, while individual
actions may use auxiliary local `TraceDB` instances and explicitly export
selected results back into the pipeline record.

## Current Status

The high-level compiler architecture is accepted and documented under
`docs/design/`.

Current open gaps are:

- minimal package and verification tooling
- the first executable compiler slice

See [docs/todo/README.md](docs/todo/README.md) for the tracked gaps.

## Read Next

- [docs/story.md](docs/story.md) — project story and motivation
- [docs/design/compiler_framework.md](docs/design/compiler_framework.md) —
  umbrella architecture
- [docs/design/compiler_syntax.md](docs/design/compiler_syntax.md) — syntax
  design
- [docs/design/compiler_semantics.md](docs/design/compiler_semantics.md) —
  semantics design
- [docs/design/compiler_passes.md](docs/design/compiler_passes.md) — compiler
  actions and pipeline design
- [docs/design/README.md](docs/design/README.md) — accepted design index
- [docs/todo/README.md](docs/todo/README.md) — remaining feature gaps
- [AGENTS.md](AGENTS.md) — repo-local agent operating rules
