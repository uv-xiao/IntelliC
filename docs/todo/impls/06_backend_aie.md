# Impl: AIE Backend (MLIR-AIE artifact emission)

## Goal

Compile spatial/dataflow programs into MLIR-AIE artifacts with explicit:

- tile mapping (spatial placement)
- FIFO/stream definitions (dataflow wiring)
- host glue for invocation

This backend emits **MLIR-AIE** (and sidecars) as the primary codegen artifacts consumed by MLIR-AIE toolchains.

Important distinction:

- this backend is **not** the definition of “compilation island” in HTP’s IR sense.
- a “compilation island” refers to an internal round-trip: AST → MLIR → passes → AST, documented in
  `docs/design/impls/12_mlir_roundtrip_island.md`.

---

## 1) Backend identity

- `backend`: `aie`
- `variant`: (optional) toolchain family, e.g. `mlir-aie`
- `hardware_profile`: e.g. `amd-xdna2:<profile-id>` (tile grid, memories, DMA capabilities)

---

## 2) Emission interface (what the backend must provide)

The AIE backend must specify:

- **eligibility**: which HTP programs/regions are emit-able to MLIR-AIE (explicit subset rules)
- **export**: how typed Python AST + layout/effects are translated into:
  - `aie.mlir`
  - sidecar JSON (mapping/fifos) for stable diffs and auditability
- **toolchain contract**: how MLIR-AIE tooling consumes the emitted artifacts (recorded in the manifest)

Replay constraint:

- HTP stages remain runnable in `mode="sim"` via Python stage programs; the existence of MLIR-AIE artifacts does not imply
  the canonical IR becomes MLIR.

---

## 3) Artifact contract: required outputs under `codegen/aie/`

Recommended layout:

```
codegen/aie/
  aie.mlir                      # MLIR-AIE module (authoritative toolchain input)
  mapping.json                  # stable placement decisions (sidecar)
  fifos.json                    # stable stream wiring decisions (sidecar)
  host.*                        # optional host glue, depending on toolchain integration
  toolchain.json                # pinned tool versions and build flags
  aie_codegen.json              # HTP-owned index of artifacts + entrypoints
```

Required semantics:

- `aie.mlir` is the authoritative MLIR-AIE module for this package.
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
- `extensions.aie.mlir`: path to `codegen/aie/aie.mlir`
- `extensions.aie.sidecars`: paths to `mapping.json`, `fifos.json`, etc.
- `extensions.aie.runtime_contract`: host runtime expectation (if any)

---

## 5) Layout + effects interaction (what must be explicit)

- distribution facet drives sharding across the virtual grid (mesh → tile mapping)
- hardware facet constrains which buffers live in which tile memories / banks
- memory facet influences packing, DMA burst patterns, and alignment legality
- channel effects must be discharged into concrete FIFO semantics (depth, protocol) for MLIR-AIE emission

Any mismatch must be reported as an unsatisfied capability/effect/layout constraint (solver-style), not as a late MLIR
lowering crash.

---

## 6) Recommended pass split: plan vs emit (analysis + transform)

To keep the island maintainable over years, split the island work into two explicit layers:

1) **planning analyses** (staged, serializable):
   - mapping decisions (tile placement, buffer placement)
   - FIFO decisions (depth, protocol, endpoints)
   - DMA routing decisions (when explicit)
2) **emission transforms**:
   - generate `aie.mlir`
   - generate `host.*`
   - generate sidecars (`mapping.json`, `fifos.json`, `toolchain.json`)

This aligns with HTP’s “pass can mutate AST and/or produce analysis” principle:

- analysis passes preserve runnable Python stages and produce `ir/stages/<id>/analysis/*`
- emit passes generate `codegen/aie/aie.mlir` and sidecars while keeping stage replay runnable in `mode="sim"`

See pass effect model: `docs/design/impls/02_pass_manager.md`.

---

## 7) Replay and verification (practical)

Because stage programs are runnable in `mode="sim"`, developers/agents can:

- replay intermediate stages to verify transforms independent of MLIR-AIE tooling
- diff staged analyses (mapping/FIFO plans) to understand changes

MLIR-AIE artifacts are then the backend integration outputs, not the debugging substrate.

---

## 8) Capability gates (how the solver prevents late MLIR failures)

The AIE backend should declare capabilities such as:

- `Backend.AIE(variant=mlir-aie)`
- `Arch.Grid(dim=2, family=xdna2)`
- `Arch.Streams` / `Arch.FIFO`
- `Arch.DMA(kind=...)`
- and any toolchain contract ids

The AIE emission pass requires these capabilities. If they are missing, the solver fails before running MLIR-AIE tooling,
and the failure report points to:

- which region required AIE emission,
- which capabilities are missing,
- and which backend packages could provide them (if registered).

Deep dive: `docs/design/impls/03_capability_solver.md`.

---

## 9) “Ready to implement” checklist (AIE backend)

Design completeness requires:

- an eligibility matcher that is explicit and testable,
- staged mapping/FIFO analyses (sidecars are stable diffs),
- an artifact validator that enforces the AIE file contract under `codegen/aie/`,
- and a toolchain contract/pinning story in the manifest.
