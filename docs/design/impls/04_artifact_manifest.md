# Impl: Artifact Manifest Schema

## Goals

- stable integration contract
- reproducibility and auditability
- backend-specific extension fields without breaking core readers
- stage replay: every intermediate stage is a “context pack” (AST + metadata + runnable Python in `sim`)

---

## Core fields (recommended)

- `htp_version`, `git_hash`, `build_env`
- `inputs`:
  - entrypoints
  - enabled dialects
  - intrinsic sets
- `target`:
  - backend name
  - hardware profile
- `pipeline`:
  - pass list with versions and parameters
- `outputs`:
  - emitted files with semantic roles
  - entry symbols and callable signatures
- `stages`:
  - stage graph metadata (per-pass stage snapshots)
- `replay`:
  - runnable Python entrypoints + supported modes (`sim|device`)
  - current stage pointer and runnable contract for that stage

## Extensibility

- `extensions` namespace for backend/dialect-specific structured fields.

---

## Stage records (what must be captured, concretely)

The manifest’s `stages.graph[]` entries should be sufficient to:

- locate the stage dumps (`dir`),
- identify what produced them (`pass`),
- understand replay availability (`runnable_py`),
- and locate analyses (for transform justification and agent loops).

Recommended per-stage fields (illustrative):

- `id`, `dir`
- `pass`: `null` for capture, or `pass_id@version`
- `runnable_py`:
  - `status`: `preserves|stubbed`
  - `modes`: `["sim", "device"]` subset
  - `program_py`: path (stage-relative)
- `analysis_index`: path to `analysis/index.json` (if present)
- optional `ids`:
  - `entities`: path to `ids/entities.json`
  - `bindings`: path to `ids/bindings.json`
- optional `maps`:
  - `entity_map`: path to `maps/entity_map.json` (major rewrites)
  - `binding_map`: path to `maps/binding_map.json` (when bindings change)
- optional `digests`:
  - `ast_hash`, `types_hash`, `effects_hash`, `analysis_hash` (semantic or byte hashes)

Digests are not required for correctness, but they make long-term regression triage and caching dramatically easier.

---

## Minimal example (illustrative JSON)

```json
{
  "schema": "htp.manifest.v1",
  "htp_version": "0.1.0-dev",
  "git_hash": "<repo-hash>",
  "build_env": {
    "python": "3.11.7",
    "platform": "linux-x86_64"
  },
  "inputs": {
    "entrypoints": [
      {"kind": "workload", "name": "add"},
      {"kind": "kernel", "name": "add_tile"}
    ],
    "dialects": ["wsp"],
    "intrinsic_sets": ["portable", "pto"]
  },
  "target": {
    "backend": "pto",
    "variant": "a2a3sim",
    "hardware_profile": "ascend:<profile-id>"
  },
  "capabilities": [
    "Dialect.WSPEnabled",
    "Layout.FacetSupported(dist)",
    "Layout.FacetSupported(mem)",
    "Backend.PTO(variant=a2a3sim)"
  ],
  "pipeline": {
    "name": "pto_default",
    "passes": [
      {"name": "ast_canonicalize", "version": "1"},
      {"name": "typecheck_layout_effects", "version": "1"},
      {"name": "apply_schedule", "version": "1"},
      {"name": "lower_pto", "version": "1"},
      {"name": "emit_pto_package", "version": "1"}
    ]
  },
  "stages": {
    "current": "s05",
    "graph": [
      {"id": "s00", "pass": null, "dir": "ir/stages/s00"},
      {"id": "s01", "pass": "ast_canonicalize@1", "dir": "ir/stages/s01"},
      {"id": "s02", "pass": "typecheck_layout_effects@1", "dir": "ir/stages/s02"},
      {"id": "s03", "pass": "apply_schedule@1", "dir": "ir/stages/s03"},
      {"id": "s04", "pass": "lower_pto@1", "dir": "ir/stages/s04"},
      {"id": "s05", "pass": "emit_pto_package@1", "dir": "ir/stages/s05"}
    ]
  },
  "replay": {
    "entrypoints": [{"name": "add", "kind": "workload"}],
    "modes": ["sim", "device"],
    "default_mode": "sim",
    "stage_program": "ir/stages/s05/program.py"
  },
  "outputs": {
    "kernel_config": "codegen/pto/kernel_config.py",
    "pto_codegen_index": "codegen/pto/pto_codegen.json",
    "entrypoints": [
      {"name": "add", "kind": "workload", "signature": "(*inputs) -> None"}
    ]
  },
  "extensions": {
    "pto": {
      "toolchain": "cann:<ver>",
      "runtime_contract": "pto-runtime:<ver>"
    }
  }
}
```

---

## Recommended companion files (artifact contract)

The manifest is the index, but a complete package should also include:

- `ir/pass_trace.jsonl` (contracted per-pass trace)
- per-stage dumps:
  - `ir/stages/<id>/program.py` (runnable replay in `mode="sim"`; may be stubbed with explicit diagnostics)
  - `ir/stages/<id>/program.pyast.json` (canonical AST)
  - `ir/stages/<id>/types.json`, `layout.json`, `effects.json`, `schedule.json`
  - `ir/stages/<id>/ids/entities.json` and `ids/bindings.json` (stable construct and binding identities)
  - optional `ir/stages/<id>/maps/entity_map.json` and `maps/binding_map.json` (major rewrite provenance)
  - `ir/stages/<id>/analysis/index.json` + analysis result files (typed, versioned pass analyses)
  - `ir/stages/<id>/summary.json`

Design note: this is what makes HTP “agent-friendly by construction”: tools/agents can replay and diff stages without
re-implementing an IR interpreter.
