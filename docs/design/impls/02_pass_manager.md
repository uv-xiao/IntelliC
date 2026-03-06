# Impl: Pass Manager (contract-driven execution + tracing)

## Goal

Make pipelines **safe to compose**, **easy to debug**, and **retargetable** by enforcing three non-negotiables:

1) explicit pass contracts (`requires/provides/invalidates` + invariants),
2) deterministic replayable staging (every pass leaves an inspectable stage),
3) a first-class distinction between:
   - **AST mutation** (producing a new runnable Python stage program), and
   - **analysis production** (emitting typed data structures for downstream passes and humans/agents).

This is the unit that prevents the “implicit invariants + undocumented ordering” trap common in pass-based systems.

---

## 1) Pass effects: transform vs analysis (the key distinction)

During the compilation pipeline a pass may have two kinds of observable effects:

### 1.1 Transform effect (AST mutation)

- Input: a `ProgramState` (canonical AST + typed metadata).
- Output: a *new* `ProgramState` (possibly same semantics, different structure).
- Artifact consequence: a new `ir/stages/<stage_id>/program.pyast.json` and typically a new runnable replay
  `ir/stages/<stage_id>/program.py`.

### 1.2 Analysis effect (data production)

- Input: a `ProgramState`.
- Output: one or more **analysis results** (typed, versioned data structures).
- Artifact consequence: files under `ir/stages/<stage_id>/analysis/` plus an index.

An important design rule:
> Analysis is not “hidden compiler state”. If it matters to later transforms or to debugging, it is serializable and staged.

### 1.3 Pass taxonomy (contract-visible)

Every pass declares its effect kind:

- `AnalysisPass`: produces analyses, does not mutate AST (may enrich metadata).
- `TransformPass`: mutates AST/metadata, may optionally emit analyses.
- `MixedPass`: both.

This classification is part of the contract and is recorded in `pass_trace.jsonl`.

---

## 2) In-memory model (conceptual)

The pass manager operates on a state triple:

- `ProgramState`:
  - canonical Python AST (with stable node ids, see `docs/design/impls/01_ir_model.md`)
  - typed metadata snapshots (`types/layout/effects/schedule`)
- `CapabilityState`: a set of capability tags (incl. “analysis available” facts)
- `AnalysisStore`: a map of *materialized* analysis results keyed by `(analysis_id, version)`

Recommended analysis identity:

- `analysis_id`: `pkg::name@version` (stable)
- `schema`: `htp.analysis.<name>.vN` (JSON schema identifier)

---

## 3) Pass contract: `PassContract` (expanded)

Each pass registers a `PassContract` (conceptual schema):

- identity:
  - `pass_id`: `pkg::name@version` (stable)
  - `owner`: extension unit that provides it (dialect pkg / backend pkg / 3rd party pkg)
- effect kind:
  - `kind`: `analysis | transform | mixed`
  - `ast_effect`: `preserves | mutates`
- capability typing:
  - `requires`: capability set required before running
  - `provides`: capability set guaranteed after success
  - `invalidates`: capability set no longer guaranteed after the pass
  - convention: analyses are capabilities too, e.g. `Analysis.WarpRolePlan@1`
- invariants:
  - `requires_layout_invariants`: predicates over layout facets (e.g. “distribution normalized”)
  - `requires_effect_invariants`: predicates over effect sets (e.g. “no pending collectives”)
  - `establishes_layout_invariants`, `establishes_effect_invariants`
- analysis IO:
  - `analysis_produces`: list of `(analysis_id, schema)` items
  - `analysis_requires`: list of required analysis ids (if the pass consumes analyses)
- artifact IO:
  - `inputs`: required artifact kinds (e.g. `ir.ast_canonical`, `ir.types`, `codegen.island_outputs`)
  - `outputs`: artifact kinds this pass must emit/update (e.g. `ir.ast`, `ir.types`, `ir.effects`, `replay.program_py`)
- replay contract:
  - `runnable_py`: one of:
    - `preserves` (stage remains runnable in declared modes)
    - `stubbed` (runnable but calls stubs for unavailable regions; must emit stub metadata)
  - invariant: stages must be runnable in `mode="sim"` (see `docs/design/impls/01_ir_model.md`)
- determinism:
  - `deterministic`: `true|false`
  - if `false`, must declare nondeterminism sources and the seed/recording scheme
- diagnostics:
  - stable diagnostic codes emitted by this pass + payload schema

Design rule: if a pass consumes an analysis, it must name it in `analysis_requires`; no “just reach into global caches”.

---

## 4) Execution model (staging + invalidation)

A pipeline run is a sequence of pass invocations. For each pass invocation, the pass manager:

1) verifies `requires` (capabilities + invariants + required analyses),
2) runs the pass,
3) collects:
   - optional new `ProgramState` (if `ast_effect=mutates`),
   - analysis results (per `analysis_produces`),
4) updates `CapabilityState`:
   - add `provides`,
   - remove `invalidates`,
5) persists a new stage directory (even for analysis-only passes),
6) records a trace event and diagnostics.

### 4.1 Invalidation policy (minimum viable)

When a pass mutates AST, analyses that depend on AST structure are conservatively invalidated unless:

- the pass contract explicitly preserves them, or
- the analysis declares a stability predicate that holds (advanced; optional).

This is the simplest rule that avoids subtle use-after-change bugs in long-lived pipelines.

---

## 5) Artifact emission: stage directories (expanded)

Each pass invocation produces a new immutable stage directory:

`ir/stages/<stage_id>/...`

A stage contains:

- `program.py` (host-level replay program; may be stubbed)
- `program.pyast.json` (canonical AST dump for this stage)
- `types.json`, `layout.json`, `effects.json`, `schedule.json` (typed metadata dumps)
- `analysis/`
  - `index.json` (what analyses exist in this stage, versions, schemas, and file paths)
  - one file per analysis (JSON or another stable serialization)
- `summary.json` (small index: stage id, pass id, key capabilities, runnable modes)

The top-level manifest records the stage DAG and the “current stage” pointer.

---

## 6) `pass_trace.jsonl` schema (expanded)

Emit a line-delimited JSON log at `ir/pass_trace.jsonl`. Each line is one pass invocation:

- `pass_id`, `kind`, `ast_effect`
- `stage_before`, `stage_after`
- `time_ms` (and optional breakdown)
- `requires` (declared) and `requires_satisfied` (evidence pointers)
- `cap_delta`: `provides`, `invalidates`
- `analysis`:
  - `requires`: analysis ids consumed
  - `produces`: analysis ids emitted + file paths (stage-relative)
- `runnable_py`: `preserves|stubbed`, plus `modes` and `program_py` path
- `dumps`: paths for `program.py`, `program.pyast.json`, metadata dumps, and `analysis/index.json`
- `diagnostics`: list of `{code, severity, node_id, message, payload_ref}`

Design note: `pass_trace.jsonl` is the primary “agent substrate” because it is:

- append-only,
- structured,
- and points to deterministic stage snapshots (both transformed IR and the analyses that justified it).

Complete worked example:

- Warp specialization + software pipelining staged as analysis + transforms:
  `docs/design/impls/11_case_study_warp_specialization_pipelining.md`
