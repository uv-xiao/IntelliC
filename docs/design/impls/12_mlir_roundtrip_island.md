# Impl: MLIR Round-Trip Compilation Island (AST → MLIR → passes → AST)

## Goal

Define a precise meaning for “compilation island” in HTP:

> A compilation island is an **internal IR round-trip** that temporarily represents a region in MLIR, runs MLIR passes,
> then reconstructs Python AST to continue the HTP pipeline.

This is distinct from *external toolchains* (vendor compilers, MLIR-AIE toolchains, etc.) where HTP **emits MLIR as an
artifact** and does not require a full semantic reification back into Python AST.

---

## 1) Why this exists

Some optimizations are substantially easier (or already implemented) in MLIR ecosystems:

- affine loop transforms
- canonicalization/CSE patterns at an IR level with rich rewrite infrastructure
- vectorization and bufferization-style transforms (for eligible subsets)

HTP can reuse these by:

1) translating a well-defined subset of typed Python AST into an MLIR module,
2) running a configured MLIR pass pipeline,
3) reifying the transformed MLIR back into Python AST (plus staged analyses/metadata).

The key constraint is HTP’s executable-IR invariant:

- stages must remain runnable in `mode="sim"` throughout; the island must not “steal semantics” into opaque IR.

---

## 2) Island contract (enter/exit)

An MLIR round-trip island pass must declare:

### 2.1 Eligibility (matcher)

- which AST regions are eligible to round-trip (subset boundaries must be explicit)
- which constructs are supported (loops, buffers, intrinsics, effects)

If a region is not eligible, the pass must:

- refuse early with a structured diagnostic, or
- leave the region unchanged.

#### 2.1.1 Normative v1 subset

The first implementation should not treat “eligible subset” as open-ended. A v1 round-trip island is restricted to
regions satisfying all of the following:

- **control flow**
  - straight-line statements
  - `for` loops with statically analyzable bounds/steps
  - `if` without effectful branch-local protocol constructs
- **values**
  - scalars, tensors/tiles, buffers
  - no Python objects with opaque host semantics
- **bindings**
  - lexical bindings only; no dynamic name lookup
  - no closures / captured mutable Python state
- **effects**
  - pure compute effects
  - layout annotations
  - no CSP channels
  - no unresolved async/barrier protocol effects crossing the island boundary
- **calls**
  - only intrinsics/functions with explicit MLIR lowering support in the island’s exporter/importer tables

Explicit non-goals for v1:

- exceptions
- generators / `yield`
- dynamic Python reflection
- alias-heavy mutation patterns without an explicit buffer model
- protocol-heavy CSP subgraphs

If a candidate region violates any of these, the island pass must reject it with a stable diagnostic code rather than
partially translating it.

### 2.2 Export (AST → MLIR)

Export produces:

- `ir/stages/<id>/islands/<island_id>/input.mlir`
- a structured “lowering ledger” that ties MLIR ops back to HTP identities:
  - `entity_id` anchors for constructs
  - `binding_id` anchors for variables/bindings

The ledger is necessary to make reification deterministic and to support later diff/debug workflows.

Recommended minimum `ledger.json` shape:

```json
{
  "schema": "htp.island.ledger.v1",
  "island_id": "mlir_roundtrip_0",
  "stage_before": "s05",
  "def_id": "module::matmul_tile",
  "entity_links": [
    {
      "entity_id": "module::matmul_tile:E12",
      "role": "loop_k",
      "mlir_ops": ["%op17", "%op18"]
    }
  ],
  "binding_links": [
    {
      "binding_id": "module::matmul_tile:S3:B1",
      "name": "k",
      "mlir_values": ["%arg2", "%iv0"]
    }
  ],
  "region_roots": [
    {
      "entity_id": "module::matmul_tile:E12",
      "mlir_block": "^bb0"
    }
  ]
}
```

Constraints:

- `entity_links` must be sufficient to rebuild construct-level identity after MLIR rewrites.
- `binding_links` must be sufficient to rebuild variable identity even if MLIR renames or clones SSA values.
- the ledger is normative for import; reification must not depend on textual MLIR pattern guessing alone.

### 2.3 Transform (MLIR passes)

Run an explicit MLIR pass pipeline and emit:

- `ir/stages/<id>/islands/<island_id>/pipeline.txt` (pass pipeline description)
- `ir/stages/<id>/islands/<island_id>/output.mlir`
- optional MLIR pass dumps (when configured)

Normative constraint:

- the MLIR pass pipeline used by an island must be recorded exactly enough to replay the transformation deterministically
  (pass names, parameters, and pipeline ordering).

### 2.4 Import (MLIR → AST)

Reify the transformed MLIR back into Python AST:

- produce a new canonical AST region that reflects the IR changes
- preserve or update `entity_id` and `binding_id` as appropriate
- for major rewrites, emit mapping files:
  - `maps/entity_map.json`
  - `maps/binding_map.json`

Import must ensure:

- the stage remains runnable in `mode="sim"` (no opaque “MLIR-only” semantics)
- effects/layout obligations remain explicit and checkable in HTP metadata

Import policy for common rewrite classes:

- **preserve**: if MLIR rewrites preserve a construct semantically, keep its `entity_id`
- **split/fuse**: emit `maps/entity_map.json` with one-to-many or many-to-one mappings
- **rename/rebind**: preserve `binding_id` when semantics are unchanged; otherwise emit `maps/binding_map.json`
- **introduce helper temporaries**: assign fresh `binding_id`s and record provenance in `binding_map.json`

If import cannot reconstruct a well-formed Python AST region with explicit identities/effects, the island pass must fail
with a structured diagnostic rather than silently degrading the stage.

---

## 3) Artifact outputs (recommended)

An island run should leave behind enough evidence for humans and agents:

```
ir/stages/<stage_id>/
  islands/
    <island_id>/
      input.mlir
      output.mlir
      pipeline.txt
      ledger.json
```

This keeps the round-trip auditable without turning MLIR into HTP’s canonical IR.

Recommended companion metadata:

- `eligibility.json`
  - records which matcher rules were satisfied
- `import_summary.json`
  - counts preserved/split/fused entities and bindings

---

## 4) Relationship to external toolchains

External toolchains are a different boundary:

- HTP emits MLIR (or other IR) as **codegen artifacts** under `codegen/<backend>/...`
- the binding/toolchain consumes those artifacts to produce runnable binaries
- HTP does not require a semantic MLIR → AST reification for such toolchain steps

Example: MLIR-AIE as a backend artifact emission path is specified in `docs/design/impls/06_backend_aie.md`.
