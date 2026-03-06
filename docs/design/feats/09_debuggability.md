# Feature: Debuggability & Introspection

## Goal

Make compiler and runtime behavior observable and explainable.

HTP’s debug thesis: debugging must be possible *from artifacts alone*.

- If something fails, the package must contain enough evidence to explain:
  - what the compiler believed (types/layout/effects),
  - what changed (pass trace + stage diffs),
  - and why it is illegal (capability/effect/layout contracts).

This is critical for retargetability (cross-backend failures must be diagnosable) and for agentic development (agents need
structured traces and stable blame).

---

## Required diagnostics

- capability mismatch diagnostics (missing dialect/intrinsic/pass)
- layout incompatibility diagnostics (where, expected/got, suggested relayout)
- stream protocol/effect diagnostics (mismatched put/get, deadlock cycles)
- backend handler diagnostics (missing lowering/emitter)

### Diagnostic shape (contract)

Every diagnostic must include:

- `code`: stable identifier (e.g. `HTP.CAP.MISSING`, `HTP.LAYOUT.INCOMPAT`, `HTP.EFFECT.UNDISCHARGED`)
- `severity`: `error|warning|info`
- `node_id`: stable stage-local node id (see `docs/design/impls/01_ir_model.md`)
- `message`: short human-readable summary (non-normative)
- `payload_ref`: pointer to structured payload JSON (normative)

The payload schema is what tools/agents consume; the message is for humans.

---

## Required artifacts

- pass trace (`pass_trace.jsonl`)
- stage dumps (`ir/stages/<id>/...`):
  - `program.pyast.json` (canonical AST)
  - `types.json`, `layout.json`, `effects.json`, `schedule.json`
  - `program.py` always exists and is runnable in `mode="sim"` (may be stubbed with explicit diagnostics)
- backend-specific codegen outputs
- manifest with full pipeline info and versions

---

## Semantic diff (stage-to-stage)

HTP should treat “diffability” as a contract:

- stage dumps are deterministic and stable-ordered,
- node ids enable blame without requiring full AST structural matching,
- optional `node_id_map.json` can be emitted by large rewrites for richer diffs.

The canonical “what changed” view for a package is:

- `ir/pass_trace.jsonl` (what ran, what it claimed to do),
- plus a stage diff of `types/layout/effects` for the blamed node ids.

Rationale: MLIR textual diffs are noisy; AST + structured metadata diffs are stable and tool-friendly.
