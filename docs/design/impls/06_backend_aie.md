# Impl: AIE Backend (MLIR-AIE island contract)

## Goal

Compile spatial/dataflow programs into MLIR-AIE artifacts with explicit:

- tile mapping (spatial placement)
- FIFO/stream definitions (dataflow wiring)
- host glue for invocation

This backend is an example of an **external compilation island**: HTP’s canonical IR remains Python AST, but a contracted
pass exports a region into MLIR-AIE and imports the produced artifacts back as an island handle.

---

## 1) Backend identity

- `backend`: `aie`
- `variant`: (optional) toolchain family, e.g. `mlir-aie`
- `hardware_profile`: e.g. `amd-xdna2:<profile-id>` (tile grid, memories, DMA capabilities)

---

## 2) Island interface (enter/exit contract)

An AIE island pass must declare:

- **matcher**: which AST regions are eligible (e.g. `df_region` / CSP subgraph with static channels)
- **exporter**: how to translate canonical AST + layout/effects into:
  - `aie.mlir`
  - sidecar JSON (mapping/fifos) needed for inspection and stable diffs
- **importer**: how to rejoin the pipeline:
  - replace the exported region with a typed stub node, e.g. `IslandCall(island_id, signature, effects)`
  - ensure `RunnablePy` remains possible by routing calls through `htp.runtime.islands.invoke(island_id, ...)`
- **artifact contract**: exact file set and naming under `codegen/aie/islands/<island_id>/...`

This is the mechanism that keeps “MLIR is used here” explicit and auditable, rather than leaking MLIR invariants into the
rest of HTP.

---

## 3) Artifact contract: required outputs under `codegen/aie/`

Recommended layout:

```
codegen/aie/
  islands/
    <island_id>/
      aie.mlir
      mapping.json
      fifos.json
      host.cpp                  # or host.mlir, depending on toolchain integration
      toolchain.json            # pinned tool versions and build flags
  aie_codegen.json              # HTP-owned index of islands + entrypoints
```

Required semantics:

- `aie.mlir` is the authoritative MLIR-AIE module for this island.
- `mapping.json` is a stable, structured view of placement decisions:
  - compute tile coordinates
  - buffer placements (memory banks/spaces)
  - DMA routing decisions (when explicit)
- `fifos.json` is a stable, structured view of stream wiring:
  - FIFO ids, element types, depths
  - producer/consumer endpoints and rates (when known)

Rationale: MLIR textual diffs are noisy; sidecar JSON provides stable auditability and agent-friendly diffs.

---

## 4) Manifest extensions (`manifest.json` → `extensions.aie`)

Recommended fields:

- `extensions.aie.toolchain_contract`: `mlir-aie:<ver-or-git>`
- `extensions.aie.islands`: list of `{island_id, dir, entrypoints}`
- `extensions.aie.runtime_contract`: host runtime expectation (if any)

---

## 5) Layout + effects interaction (what must be explicit)

- distribution facet drives sharding across the virtual grid (mesh → tile mapping)
- hardware facet constrains which buffers live in which tile memories / banks
- memory facet influences packing, DMA burst patterns, and alignment legality
- channel effects must be discharged into concrete FIFO semantics (depth, protocol) at island boundary

Any mismatch must be reported as an unsatisfied capability/effect/layout constraint (solver-style), not as a late MLIR
lowering crash.
