# HTP (Heterogeneous Tile Programming) — Architecture (HOW)

## 0. Architectural snapshot

HTP is a Python-driven compiler framework with:

- **AST-first IR**: Python AST + attached typed metadata.
- **Capability typing**: every pass/pipeline/backend declares `requires/provides`.
- **Unified layout typing**: distribution + memory + hardware facets.
- **Artifact-first output**: compilation emits a package with a manifest and dumps.
- **Agent-native substrate**: replayable stage programs + staged analyses + machine-localizing diagnostics and provenance.
- **Backend plugins**: codegen emitters + bindings are backend-registered.

This file describes components and data flow; implementation deep dives are in `docs/design/impls/`.

Related design references already captured in this repo:

- Artifact packaging patterns: `docs/reference/18_pypto.md`
- Hardware abstraction (hierarchy + memory spaces): `docs/reference/19_arknife.md`
- Unified layout across layers: `docs/reference/20_axe.md`
- Stream/layout typing and mapping concepts: `docs/reference/16_dato.md`
- AIE mapping + FIFOs reference shape: `docs/reference/15_allo.md`

Case study (end-to-end, pass-by-pass):

- Warp specialization + software pipelining: `docs/design/impls/11_case_study_warp_specialization_pipelining.md`

---

## 1. Top-level data flow

1. **Parse & capture**: the Python entrypoints (kernels/workloads/routines) are captured as AST + symbol tables.
2. **Dialect expansion**: dialect-level syntactic sugar expands into canonical AST forms and attaches metadata.
3. **Type/effect checking**: layout facets + stream effects are validated; required collectives/effects are made explicit.
4. **Pipeline selection**: given `target_backend`, choose a pipeline whose `requires` are satisfied by the program’s
   dialects/intrinsics/layout capabilities.
5. **Lowering and codegen**:
   - AST passes perform canonicalization, scheduling, partitioning, and lowering into codegen-ready forms.
   - Optional IR islands round-trip regions through MLIR (AST → MLIR → passes → AST).
6. **Emit artifact package**: a stable directory tree with manifest, IR dumps, codegen outputs, and build/run metadata.
7. **Bind**: backend binding builds/loads/executes (or returns a build recipe) from the package.

---

## 2. Core component model

### 2.1 Program model

A **Program** (design-time concept) includes:

- entrypoints:
  - kernels (device functions)
  - workloads (task graphs)
  - routines (host orchestration)
- enabled dialects (e.g., WSP, CSP)
- imported intrinsic sets (portable + backend-specific)
- layout declarations/annotations
- target selection (backend + hardware profile)

### 2.2 AST representation + metadata

HTP treats AST as the canonical source and attaches metadata:

- type info:
  - scalar/tile dtypes and shapes
  - layout facets (distribution/memory/hardware)
- schedule directives:
  - fusion hints, pipelining stages, buffering, resource constraints
- lowering state:
  - normalized forms, explicit collectives, explicit stream ops

Metadata must be:

- serializable into artifact dumps (for reproducibility),
- stable under minor AST reshaping (keyed by node identity + symbol path).

### 2.3 Dialect packages

Each dialect package includes:

- Python surface API (decorators, helper functions)
- AST patterns and canonical forms
- typing rules (layout + effects)
- canonicalization/lowering passes
- declared capabilities (what this dialect provides)

### 2.4 Intrinsic sets

An intrinsic set is:

- a typed API surface (Python calls) with contracts,
- a registry of backend handlers:
  - lowering rules (AST → backend form)
  - emitter code (backend form → artifact files)

Intrinsic contracts are the key compatibility boundary:

- required layout facets
- permitted memory spaces
- required scheduling constraints

### 2.5 Layout & effect typing

HTP should separate:

- **Layout values** attached to tensors/tiles.
- **Typing rules**:
  - distribution join/compatibility and explicit relayout
  - memory layout legality for vectorization/packing
  - hardware placement constraints (e.g., “this buffer must be in UB”)
- **Effects**:
  - stream effects (linear/affine usage)
  - collective effects (pending reductions, barriers)

### 2.6 Passes

A pass is a contracted unit that may:

- **mutate the typed Python AST** (producing a new runnable stage program), and/or
- **produce analyses** (typed data structures) that are staged and serializable.

This distinction is explicit in the pass contract (`kind`, `ast_effect`) and recorded in stage artifacts.

A pass has a contract:

- `requires`: capabilities that must exist beforehand
- `provides`: capabilities established after it runs
- invariants:
  - AST shape invariants
  - type invariants (e.g., “all distribution layouts normalized”)
  - effect invariants (e.g., “no pending collectives”)

Passes come in classes:

- AST passes (primary)
- IR-island passes (AST → MLIR → passes → AST)
- packaging passes (manifest, file layout, dependency closure)

### 2.7 Pipelines

A pipeline is:

- a target-specific pass list with parameters,
- a declared output artifact contract,
- a binding requirement (which binding can run this package).

Pipeline selection is constraint solving:

- program capabilities + target backend requirements must satisfy the pipeline’s `requires`.

### 2.8 Backends and bindings

Backends provide:

- hardware model definition(s)
- supported dialects/intrinsics
- codegen emitters
- package contract

Bindings provide:

- build toolchain integration (compile/assemble/package)
- load/execute/simulate integration
- trace and diagnostics hooks

### 2.9 Long-term architecture (module boundaries and stable seams)

To keep the system extensible for years, HTP should be built around a small number of stable seams:

- `htp.frontend`: capture decorators/APIs into canonical AST entrypoints
- `htp.ir`: node ids, canonical AST forms, typed metadata snapshots, analysis staging utilities
- `htp.pass`: pass contracts, pass manager, tracing, stage emission
- `htp.pipeline`: pipeline templates + capability solver
- `htp.artifacts`: package writer, manifest schema, validators, semantic diff tools
- `htp.dialects`: dialect packages (WSP/CSP/etc.) as extension units
- `htp.intrinsics`: intrinsic sets and backend handler registries
- `htp.backends`: backend plugins (ArchModel + codegen emitters)
- `htp.bindings`: build/load/run integrations (pto-runtime, NV-GPU toolchains/runtimes, MLIR-AIE toolchains, etc.)
- `htp.runtime`: the normative replay shim surface (`default_runtime`, `call_kernel`, `intrinsics.invoke`,
  `extensions.invoke`, `raise_stub`)
- `htp.agent`: agent loop, policy, and verification orchestration (developer tooling)

Design rule: anything that affects semantics or legality must be visible at these seams as typed layout/effects,
capabilities, or staged analyses. Hidden “one-off” invariants do not scale.

---

## 3. Artifact package contract (normative v1 baseline)

Directory layout (illustrative):

```
<out>/
  manifest.json
  ir/
    pass_trace.jsonl
    stages/
      s00/
        program.py
        replay/
          stubs.json                # required when runnable_py=stubbed
        program.pyast.json
        env.json
        types.json
        layout.json
        effects.json
        schedule.json
        ids/
          entities.json
          bindings.json
        maps/                       # optional (major rewrites)
          entity_map.json
          binding_map.json
        analysis/
          index.json
        summary.json
      s01/
        ...
  codegen/
    <backend>/
      ... backend-specific outputs ...
  build/
    ... build recipes / toolchain metadata ...
  logs/
    ... optional build/run logs ...
```

The manifest must include:

- compilation identity (versions, git hashes, environment capture)
- enabled dialects and intrinsic sets
- pipeline list and pass parameters
- backend target and hardware profile
- entrypoints (kernel/routine symbols)
- produced artifacts with paths and semantics
- replay info:
  - runnable python entrypoints
  - supported modes (`sim|device`)
  - current stage pointer

Deep dive: `docs/design/impls/04_artifact_manifest.md`.

---

## 4. Target-specific packaging sketches

### 4.1 PTO / Ascend backend

Recommended shape (mirrors proven kernel/orchestration separation patterns):

```
codegen/pto/
  kernel_config.py
  kernels/
    aiv/
    aic/                   # optional
  orchestration/
  ptoas/                   # optional intermediates
  pto_codegen.json
  build/
    toolchain.json
```

Key design point: `kernel_config.py` is the runner-facing bridge (existing tooling expects it); HTP keeps a stable
`pto_codegen.json` above runner-specific ids.

Deep dive: `docs/design/impls/05_backend_pto.md`.

### 4.2 NV-GPU backend

Recommended shape:

```
codegen/nvgpu/
  kernels/
  host/
  nvgpu_codegen.json
  build/
    toolchain.json
```

Deep dive: `docs/design/impls/13_backend_nvgpu.md`.

### 4.3 Optional extension backend: AIE (MLIR-AIE)

Recommended shape:

```
codegen/aie/
  aie.mlir
  mapping.json
  fifos.json
  host.cpp (or host.mlir)        # optional, depends on toolchain integration
  toolchain.json                  # pinned tool versions and build flags
  aie_codegen.json                # HTP-owned index of artifacts + entrypoints
```

Deep dive: `docs/design/impls/06_backend_aie.md`.

---

## 5. Cross-cutting concerns

### 5.1 Diagnostics

- “capability mismatch”: pipeline requires missing dialect/intrinsic/layout capability.
- “layout incompatibility”: distribution join failures; missing relayout.
- “effect mismatch”: stream protocol mismatch; pending collectives not discharged.
- “backend handler missing”: intrinsic lacks lowering/emitter for backend.

### 5.2 Testing strategy (docs-only requirement)

- Golden artifact tests: compile example → compare manifest + key emitted files.
- Type-check tests: known-bad programs produce stable diagnostics.
- Backend contract tests: package validates against binding expectations.

Deep dive: `docs/design/impls/08_testing.md`.

---

## 6. Deep dives index

Implementation deep dives live in:

- `docs/design/impls/01_ir_model.md`
- `docs/design/impls/02_pass_manager.md`
- `docs/design/impls/03_capability_solver.md`
- `docs/design/impls/04_artifact_manifest.md`
- `docs/design/impls/05_backend_pto.md`
- `docs/design/impls/06_backend_aie.md`
- `docs/design/impls/07_binding_interface.md`
- `docs/design/impls/08_testing.md`
- `docs/design/impls/09_transition_plan.md`
- `docs/design/impls/10_agentic_tooling.md`
- `docs/design/impls/11_case_study_warp_specialization_pipelining.md`
- `docs/design/impls/12_mlir_roundtrip_island.md`
