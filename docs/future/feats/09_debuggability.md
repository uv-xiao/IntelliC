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
- `fix_hints_ref`: pointer to structured remediation hints (normative for v1, may point to an empty list)

The payload schema and fix-hint schema are what tools/agents consume; the message is for humans.

### Replay/stub diagnostics (required family)

Because stage replay is mandatory in `mode="sim"`, stub hits must have a stable diagnostic family rather than ad-hoc
runtime errors.

Recommended codes:

- `HTP.REPLAY.STUB_HIT`
- `HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC`
- `HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY`

Recommended payload fields:

- `stage_id`
- `node_id`
- `entity_id` (when available)
- `reason`: `missing_simulator | external_toolchain_only | intentionally_unimplemented`
- `artifact_ref` (if the stub corresponds to emitted backend artifacts)
- `next_actions` (normative structured fix hints)

Recommended artifact:

- `ir/stages/<id>/replay/stubs.json` containing one structured entry per stubbed region/intrinsic

---

## Required artifacts

- pass trace (`ir/pass_trace.jsonl`)
- stage dumps (`ir/stages/<id>/...`):
  - `program.pyast.json` (canonical AST)
  - `types.json`, `layout.json`, `effects.json`, `schedule.json`
  - `ids/entities.json` and `ids/bindings.json` (stable construct and variable identities)
  - `program.py` always exists and is runnable in `mode="sim"` (may be stubbed with explicit diagnostics)
- backend-specific codegen outputs
- manifest with full pipeline info and versions

---

## Semantic diff (stage-to-stage)

HTP should treat “diffability” as a contract:

- stage dumps are deterministic and stable-ordered,
- node ids enable blame without requiring full AST structural matching,
- major rewrites emit explicit maps:
  - `maps/entity_map.json` (semantic construct mapping)
  - `maps/binding_map.json` (variable binding mapping, when bindings change)

The canonical “what changed” view for a package is:

- `ir/pass_trace.jsonl` (what ran, what it claimed to do),
- plus a stage diff of `types/layout/effects` for the blamed node ids.

Rationale: MLIR textual diffs are noisy; AST + structured metadata diffs are stable and tool-friendly.
