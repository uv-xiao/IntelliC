# Impl: Pass Manager (contract-driven execution + tracing)

## Goal

Make pipelines **safe to compose** and **easy to debug** by enforcing:

- explicit, checkable pass contracts (`requires/provides/invalidates`)
- deterministic execution (or explicit nondeterminism declarations)
- standard artifact emission (`pass_trace.jsonl`, AST/type/effect dumps, runnable Python stage programs)

This component is a key differentiator vs “IR + passes” systems that rely on implicit invariants and undocumented pass
ordering.

---

## 1) Pass contract: `PassContract`

Each pass registers as `PassContract` (conceptual schema):

- identity:
  - `pass_id`: `pkg::name@version` (stable)
  - `owner`: extension unit that provides it (dialect pkg / backend pkg / 3rd party pkg)
- capability typing:
  - `requires`: capability set required before running
  - `provides`: capability set guaranteed after success
  - `invalidates`: capability set no longer guaranteed after the pass
- invariants:
  - `requires_layout_invariants`: predicates over layout facets (e.g. “distribution normalized”)
  - `requires_effect_invariants`: predicates over effect sets (e.g. “no pending collectives”)
  - `establishes_layout_invariants`, `establishes_effect_invariants`
- artifact IO:
  - `inputs`: required artifact kinds (e.g. `ir.ast_canonical`, `ir.types`, `codegen.island_outputs`)
  - `outputs`: artifact kinds this pass must emit/update (e.g. `ir.ast`, `ir.types`, `ir.effects`, `replay.program_py`)
- replay contract:
  - `runnable_py`: one of:
    - `preserves` (stage remains runnable in declared modes)
    - `stubbed` (runnable but calls stubs for unavailable regions; must emit stub metadata)
    - `breaks` (not runnable; must provide diagnostic explaining why)
- determinism:
  - `deterministic`: `true|false`
  - if `false`, must declare the nondeterminism source (e.g. randomized search) and how it is seeded/recorded
- diagnostics:
  - stable diagnostic codes emitted by this pass + payload schema

---

## 2) Execution model

A pipeline run is a sequence of pass invocations. For each pass invocation, the pass manager:

1) verifies `requires` (capabilities + invariants),
2) runs the pass,
3) verifies that `provides` invariants hold,
4) emits standard dumps and trace events,
5) updates the program’s “capability state” and stage graph.

If a pass fails, the run terminates with:

- the pass’s structured diagnostics, and
- a solver-style failure report for “why the remainder is impossible” (when applicable).

---

## 3) Artifact emission: stage directories

Each pass invocation produces a new immutable stage directory:

`ir/stages/<stage_id>/...`

A stage contains (recommended baseline):

- `program.py` (host-level replay program; may be stubbed)
- `program.pyast.json` (canonical AST dump for this stage)
- `types.json`, `layout.json`, `effects.json`, `schedule.json` (typed metadata dumps)
- `summary.json` (small index: stage id, pass id, key capabilities)

The manifest records the stage DAG and the “current” stage pointer.

---

## 4) `pass_trace.jsonl` schema

Emit a line-delimited JSON log at `ir/pass_trace.jsonl`. Each line is one pass invocation event:

- `pass_id`
- `stage_before`, `stage_after`
- `time_ms` (and optional breakdown)
- `requires` (declared) and `requires_satisfied` (evidence pointers)
- `cap_delta`: `provides`, `invalidates`
- `runnable_py`: `preserves|stubbed|breaks`, plus `modes` and `program_py` path if present
- `dumps`: paths for `program.py`, `program.pyast.json`, and metadata dumps
- `diagnostics`: list of `{code, severity, node_id, message, payload_ref}`

Design note: `pass_trace.jsonl` is the primary “agent substrate” for debugging and automated repair loops because it is:

- append-only,
- structured,
- and directly points to deterministic IR snapshots.
