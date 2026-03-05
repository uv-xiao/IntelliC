# Feature: Backends and Artifact Contracts

## Goal

Treat backends as first-class and keep integration stable via artifact contracts.

Backends are not “a final lowering target”; they are **plugins with explicit contracts**:

- what semantics they support (capabilities, layout legality rules, effect discharge rules),
- what codegen they can emit (artifact contract),
- and what binding/runtime integration they require.

The artifact contract is the stable boundary between:

- compiler internals (passes, analyses, dialects), and
- everything else (builders, runtimes, profilers, deployment systems, agents).

---

## Backend definition must include

- hardware profile(s)
- supported dialects and intrinsic handlers
- supported layout facets and legality rules
- codegen packaging contract
- binding interface expectations
- replay expectations (whether `RunnablePy(sim|device)` is supported and how)

## Artifact contract principles

- Single compilation → single package directory
- Stable manifest schema
- Separation of:
  - generated code/artifacts
  - intermediate dumps
  - build/run metadata
- Stage replay friendliness:
  - per-stage `program.py` exists when pass contracts preserve `RunnablePy`
  - backends should provide simulators for core intrinsic semantics whenever feasible

## “Must-support” initial backends

- Ascend PTO toolchain/runtime (simulation + device)
- AIE via MLIR-AIE

---

## Backend contract checklist (what must be explicit)

For a backend `B`, the design must specify:

1) **Backend identity**
- `backend`: stable name (e.g. `pto`, `aie`)
- `variant`: optional (e.g. `a2a3sim`, `a2a3`, `xdna2`)
- `hardware_profile`: stable profile id (used to select legality rules)

2) **Capability surface**
- layout facet subsets supported
- memory spaces and constraints
- async/barrier/event model supported (as capabilities)
- intrinsic handler availability (`lower|emit|simulate`)

3) **Artifact contract**
- required file tree under `codegen/<backend>/...`
- required index files (backend-local manifests, registries)
- required version pins (toolchain, runtime contract ids)

4) **Binding contract**
- what “build” means (which toolchain; which inputs)
- what “load/run” means (sim vs device)
- what tracing hooks exist and where logs are written

Deep dive:
- PTO packaging: `docs/design/impls/05_backend_pto.md`
- AIE island packaging: `docs/design/impls/06_backend_aie.md`
- Binding interface: `docs/design/impls/07_binding_interface.md`
