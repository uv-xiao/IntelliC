# Impl: Artifact Manifest Schema

## Goals

- stable integration contract
- reproducibility and auditability
- backend-specific extension fields without breaking core readers
- stage replay: every intermediate stage is a “context pack” (AST + metadata + runnable Python in `sim`)

---

## Core fields (normative v1)

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

Required per-stage fields for v1:

- `id`, `dir`
- `pass`: `null` for capture, or `pass_id@version`
- `runnable_py`:
  - `status`: `preserves|stubbed`
  - `modes`: `["sim", "device"]` subset
  - `program_py`: path (stage-relative)
  - optional `stubs`: path to `replay/stubs.json`
- `analysis_index`: path to `analysis/index.json`
- `ids`:
  - `entities`: path to `ids/entities.json`
  - `bindings`: path to `ids/bindings.json`
- `maps`:
  - `entity_map`: path to `maps/entity_map.json` (major rewrites)
  - `binding_map`: path to `maps/binding_map.json` (when bindings change)
- `islands`:
  - list of `{island_id, dir}` for MLIR round-trip evidence under `islands/`
- `digests`:
  - `ast_hash`, `types_hash`, `effects_hash`, `analysis_hash` (semantic or byte hashes)
- `summary`: path to `summary.json`

Digests are not required for correctness, but they make long-term regression triage and caching dramatically easier.

Normalization rules:

- If a stage has no rewrite maps, `maps` must still exist with `null` values.
- If a stage has no islands, `islands` must be an empty list.
- If a stage has no analyses, `analysis_index` must still point to an empty `analysis/index.json`.
- If digests are not computed in v1, each digest field must be `null`; readers must not infer absence from missing keys.

---

## Minimal example (normative field layout)

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
      {
        "id": "s00",
        "pass": null,
        "dir": "ir/stages/s00",
        "runnable_py": {
          "status": "preserves",
          "modes": ["sim"],
          "program_py": "ir/stages/s00/program.py",
          "stubs": null
        },
        "analysis_index": "ir/stages/s00/analysis/index.json",
        "ids": {
          "entities": "ir/stages/s00/ids/entities.json",
          "bindings": "ir/stages/s00/ids/bindings.json"
        },
        "maps": {
          "entity_map": null,
          "binding_map": null
        },
        "islands": [],
        "digests": {
          "ast_hash": null,
          "types_hash": null,
          "effects_hash": null,
          "analysis_hash": null
        },
        "summary": "ir/stages/s00/summary.json"
      },
      {
        "id": "s01",
        "pass": "ast_canonicalize@1",
        "dir": "ir/stages/s01",
        "runnable_py": {
          "status": "preserves",
          "modes": ["sim"],
          "program_py": "ir/stages/s01/program.py",
          "stubs": null
        },
        "analysis_index": "ir/stages/s01/analysis/index.json",
        "ids": {
          "entities": "ir/stages/s01/ids/entities.json",
          "bindings": "ir/stages/s01/ids/bindings.json"
        },
        "maps": {
          "entity_map": null,
          "binding_map": null
        },
        "islands": [],
        "digests": {
          "ast_hash": null,
          "types_hash": null,
          "effects_hash": null,
          "analysis_hash": null
        },
        "summary": "ir/stages/s01/summary.json"
      },
      {
        "id": "s02",
        "pass": "typecheck_layout_effects@1",
        "dir": "ir/stages/s02",
        "runnable_py": {
          "status": "preserves",
          "modes": ["sim"],
          "program_py": "ir/stages/s02/program.py",
          "stubs": null
        },
        "analysis_index": "ir/stages/s02/analysis/index.json",
        "ids": {
          "entities": "ir/stages/s02/ids/entities.json",
          "bindings": "ir/stages/s02/ids/bindings.json"
        },
        "maps": {
          "entity_map": null,
          "binding_map": null
        },
        "islands": [],
        "digests": {
          "ast_hash": null,
          "types_hash": null,
          "effects_hash": null,
          "analysis_hash": null
        },
        "summary": "ir/stages/s02/summary.json"
      },
      {
        "id": "s03",
        "pass": "apply_schedule@1",
        "dir": "ir/stages/s03",
        "runnable_py": {
          "status": "preserves",
          "modes": ["sim"],
          "program_py": "ir/stages/s03/program.py",
          "stubs": null
        },
        "analysis_index": "ir/stages/s03/analysis/index.json",
        "ids": {
          "entities": "ir/stages/s03/ids/entities.json",
          "bindings": "ir/stages/s03/ids/bindings.json"
        },
        "maps": {
          "entity_map": null,
          "binding_map": null
        },
        "islands": [],
        "digests": {
          "ast_hash": null,
          "types_hash": null,
          "effects_hash": null,
          "analysis_hash": null
        },
        "summary": "ir/stages/s03/summary.json"
      },
      {
        "id": "s04",
        "pass": "lower_pto@1",
        "dir": "ir/stages/s04",
        "runnable_py": {
          "status": "stubbed",
          "modes": ["sim"],
          "program_py": "ir/stages/s04/program.py",
          "stubs": "ir/stages/s04/replay/stubs.json"
        },
        "analysis_index": "ir/stages/s04/analysis/index.json",
        "ids": {
          "entities": "ir/stages/s04/ids/entities.json",
          "bindings": "ir/stages/s04/ids/bindings.json"
        },
        "maps": {
          "entity_map": "ir/stages/s04/maps/entity_map.json",
          "binding_map": null
        },
        "islands": [],
        "digests": {
          "ast_hash": null,
          "types_hash": null,
          "effects_hash": null,
          "analysis_hash": null
        },
        "summary": "ir/stages/s04/summary.json"
      },
      {
        "id": "s05",
        "pass": "emit_pto_package@1",
        "dir": "ir/stages/s05",
        "runnable_py": {
          "status": "stubbed",
          "modes": ["sim", "device"],
          "program_py": "ir/stages/s05/program.py",
          "stubs": "ir/stages/s05/replay/stubs.json"
        },
        "analysis_index": "ir/stages/s05/analysis/index.json",
        "ids": {
          "entities": "ir/stages/s05/ids/entities.json",
          "bindings": "ir/stages/s05/ids/bindings.json"
        },
        "maps": {
          "entity_map": null,
          "binding_map": null
        },
        "islands": [],
        "digests": {
          "ast_hash": null,
          "types_hash": null,
          "effects_hash": null,
          "analysis_hash": null
        },
        "summary": "ir/stages/s05/summary.json"
      }
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

## Required companion files (artifact contract)

The manifest is the index, but a complete package should also include:

- `ir/pass_trace.jsonl` (contracted per-pass trace)
- per-stage dumps:
  - `ir/stages/<id>/program.py` (runnable replay in `mode="sim"`; may be stubbed with explicit diagnostics)
  - optional `ir/stages/<id>/replay/stubs.json` (typed stub metadata for replay-time diagnostics)
  - `ir/stages/<id>/program.pyast.json` (canonical AST)
  - `ir/stages/<id>/types.json`, `layout.json`, `effects.json`, `schedule.json`
  - `ir/stages/<id>/ids/entities.json` and `ids/bindings.json` (stable construct and binding identities)
  - optional `ir/stages/<id>/maps/entity_map.json` and `maps/binding_map.json` (major rewrite provenance)
  - optional `ir/stages/<id>/islands/<island_id>/...` (MLIR round-trip evidence: input/output MLIR, pipeline, ledger)
  - `ir/stages/<id>/analysis/index.json` + analysis result files (typed, versioned pass analyses)
  - `ir/stages/<id>/summary.json`

Design note: this is what makes HTP “agent-friendly by construction”: tools/agents can replay and diff stages without
re-implementing an IR interpreter.

## Manifest invariants that validators must enforce

- `schema` must be `htp.manifest.v1`.
- `stages.current` must name an entry in `stages.graph`.
- every `stages.graph[].dir` must exist.
- every stage record must point to an existing `program.py`, `program.pyast.json`, `types.json`, `layout.json`,
  `effects.json`, `schedule.json`, `ids/entities.json`, `ids/bindings.json`, `analysis/index.json`, and `summary.json`.
- if `runnable_py.status == "stubbed"`, `runnable_py.stubs` must be non-null and point to `replay/stubs.json`.
- every path under `outputs` and `extensions.*` must be package-relative, not absolute.
