# AST-All-the-Way Contract

This document is the unified implemented contract for HTP's AST-all-the-way
redesign. It replaces the completed in-progress design drafts with a stable
`docs/design/` entry that explains the current architecture, the rationale, and
the code paths that enforce it.

## Why this topic exists

HTP's primary goal is to build a compiler stack that is both human-friendly and
LLM-friendly.

That goal has a concrete technical meaning:

- human-friendly: authored programs and intermediate artifacts remain readable,
  editable native Python rather than compiler-only payload blobs
- LLM-friendly: mutated intermediate artifacts remain reparsable and executable
  through a Python interpreter or structured replay diagnostic
- retargetable: backends and extension islands may participate, but they do not
  become the semantic owner at global compiler boundaries

The route to that goal is **AST all the way**. HTP keeps Python-space as the
canonical compiler surface while using typed Python objects to own semantics.

## Visual model

```text
human Python surface
        |
        v
typed ProgramModule object graph
        |
        +--> passes mutate or emit ProgramModule variants
        |
        v
normalized staged Python program.py
        |
        v
parse/rebuild/run through ProgramModule interpreter
```

Foreign IRs, MLIR pipelines, and backend-local forms may appear inside a pass or
extension, but the next committed global stage must return to this Python-owned
contract.

## Implemented contract

### Semantic owner

`ProgramModule` is the committed-stage semantic owner. HTP does not treat JSON
sidecars, raw Python AST nodes, or backend text as the primary semantic truth.

Python source and Python AST still matter, but as:

- authoring input,
- capture and mutation evidence,
- normalized staged artifact format,
- and a rebuildable persistence layer for typed objects.

The round-trip law is semantic rather than textual:

```text
parse/capture Python -> ProgramModule
render ProgramModule -> normalized Python
parse/rebuild normalized Python -> equivalent ProgramModule
run equivalent ProgramModule -> interpreter/replay behavior
```

The current implementation proves that law through `ProgramModule` rendering,
staged replay, and the checked-in closure example.

### Normalized HTP Python

HTP does not promise to preserve arbitrary original user syntax. Instead, it
emits normalized HTP Python that reconstructs typed compiler objects directly.

The staged `program.py` contract exposes:

- top-level readable payload bindings,
- `program_module()` for typed inspection,
- `program_state()` for compatibility state export,
- and `run(...)` for interpreter-backed replay.

The renderer intentionally avoids one opaque inline blob. The artifact should be
readable enough for humans and agents to inspect, edit, diff, and rerun.

### IR structure

The current IR substrate is a typed Python object graph rooted at
`ProgramModule`.

Core ownership is split across:

- `ProgramItems` for top-level program families,
- typed kernel/workload semantic records,
- typed aspect wrappers for type/layout/effect/schedule facts,
- typed identity and analysis records,
- and typed dialect-local records for WSP and CSP stage/process structure.

The design direction is one shared substrate, not parallel semantic universes.
Top-level concepts such as kernels, routines, task graphs, and process graphs
should reuse common typed value, statement, identity, aspect, analysis, pass,
interpreter, and artifact mechanisms.

### Identity and references

New semantic infrastructure must avoid stringly-typed ownership when typed ids
or references are viable.

Readable names may appear in user-facing Python and artifacts, but they are not
the semantic source of truth. Stable ids, scoped bindings, entity maps, and pass
rewrite maps are the mechanism that lets HTP relate one stage to the next.

The same rule applies to payloads: dictionaries are allowed at explicit
serialization boundaries, but new semantic ownership should live in classes or
dataclasses with named fields and invariants.

### Dialects and frontends

Builtin features and extensions are both dialects. The difference is repository
ownership and packaging, not a different semantic mechanism.

A dialect may provide:

- typed nodes or records,
- aspects and analyses,
- intrinsics,
- frontend capture rules,
- interpreter handlers,
- passes,
- lowering hooks,
- and artifact renderers.

Dialect features must compose through the shared substrate. A frontend feature
clears review only when it composes across:

- parse/capture,
- typed IR ownership,
- pass execution,
- interpreter execution,
- and artifact rendering.

The implemented WSP/CSP AST frontends prove this direction. They use small
single-purpose handlers for local syntax forms and lower into the same
`ProgramModule` owner as builder-based surfaces.

### Passes and analyses

Passes consume one validated `ProgramModule` and return a pass result that
contains:

- the resulting `ProgramModule`,
- change summaries,
- invalidation or preservation evidence,
- rewrite maps,
- optional artifacts,
- and diagnostics.

Aspects are long-lived semantic state. Analyses are derived facts that must be
invalidatable. A pass must not silently depend on stale analysis state after it
has changed the object graph.

A pass may use transient internal forms, including foreign IRs, but those forms
cannot cross a committed global stage boundary unless they satisfy the same
normalized Python and replay contract.

### Stage commit rule

A pass may commit a new stage only when the result has:

- a valid typed object graph,
- valid identity, binding, and mapping state,
- valid aspect and analysis state after invalidation/revalidation,
- renderability into normalized HTP Python,
- rebuildability from that Python,
- and executable interpreter/replay semantics or a structured replay diagnostic.

This rule is what prevents AST-all-the-way from degrading into selected Python
snapshots plus opaque sidecars.

### No-legacy law

Redesign and migration branches may use transitional adapters while migrating,
but legacy parallel systems must not survive as permanent compatibility layers.

For this architecture, that means:

- no payload-first semantic path left active beside `ProgramModule`,
- no duplicate renderer or replay system kept alive after replacement,
- no sidecar-only semantic owner at committed global boundaries,
- and no old pass contract preserved if the new pass contract supersedes it.

If a future branch needs compatibility, it should be explicitly scoped as an
adapter at a boundary, not a second internal semantic model.

### Module organization

File/module organization is part of the architecture contract. The current
module ownership model is:

- `htp/ir/program/`: `ProgramModule`, stage state, composition, rendering
- `htp/ir/core/`: typed semantics, aspects, ids, layout, types, op specs
- `htp/ir/frontends/`: frontend registry and AST/rule substrate
- `htp/ir/dialects/`: dialect-local typed records and frontend handlers
- `htp/ir/interpreters/`: object-oriented interpreter dispatch
- `htp/passes/`: pass contracts and transformations
- `htp/artifacts/`: package and staged-artifact emission/validation

Architecture work should split mixed concerns before adding more logic. Public
authoring, typed semantics, serialization, registry/discovery, interpretation,
passes, and artifacts should not collapse into one monolithic helper file.

## Implemented proof points

The current implementation has concrete evidence for the contract:

- `ProgramModule` is emitted and replayed as the committed-stage owner.
- `htp.compile_program(...)` prefers registered `to_program_module()` frontend
  ingress over raw payload probing.
- WSP and CSP public surfaces own typed local structure before serialization.
- AST-backed WSP/CSP frontends lower nested Python functions into final
  `ProgramModule` state.
- `ir/stages/<id>/program.py` is pretty-printed runnable Python with readable
  top-level bindings.
- Pass contracts record Python renderability and executability preservation.
- The tile-streamed GEMM closure example validates authored, core, scheduled,
  and backend-ready variants through the same object graph and interpreter path.

## Coding pointers

Start with these files when changing this contract:

- `htp/ir/program/module.py`
- `htp/ir/program/render.py`
- `htp/ir/program/compose.py`
- `htp/ir/frontends/rules.py`
- `htp/ir/frontends/ast_context.py`
- `htp/ir/frontends/ast_handlers.py`
- `htp/ir/frontends/ast_lowering.py`
- `htp/ir/frontends/ast_visitor.py`
- `htp/ir/dialects/wsp/frontends.py`
- `htp/ir/dialects/csp/frontends.py`
- `htp/ir/interpreters/registry.py`
- `htp/ir/interpreters/entrypoints.py`
- `htp/passes/contracts.py`
- `htp/artifacts/state.py`
- `examples/tile_streamed_gemm_closure/`

Related design documents:

- `docs/design/compiler_model.md`
- `docs/design/programming_surfaces.md`
- `docs/design/pipeline_and_solver.md`
- `docs/design/artifacts_replay_debug.md`
- `docs/design/ir_infrastructure_review.md`

## Current limits

The AST-all-the-way stage contract is implemented at the current repository
scale. Remaining open product gaps are narrower:

- backend-depth work for NV-GPU, PTO runtime coverage, and AIE claims,
- broader top-level documentation alignment,
- and future frontend/backend features that must preserve the same contract.

If any future work weakens normalized Python renderability, interpreter-backed
execution, typed semantic ownership, or dialect composability, reopen a TODO
before implementation instead of treating the regression as local cleanup.
