# HTP Implemented Features

This document lists the feature surface that is **already implemented** in the repository.
It is the implemented counterpart to `docs/future/features.md`.

## 1. Compiler substrate

Implemented today:

- Python-space canonical compilation with replayable staged programs
- staged semantic payloads:
  - `kernel_ir`
  - `workload_ir`
  - `types`
  - `layout`
  - `effects`
  - `schedule`
- pass contracts, staged analyses, and pass trace emission
- explicit identity and mapping artifacts
- solver preflight with `ir/solver_failure.json`
- structured compiler failures with `ir/compiler_failure.json`
- registered pass and pipeline surfaces
- manifest enrichment with `inputs`, `pipeline`, and `capabilities`

Main anchors:

- `htp/ir/`
- `htp/passes/`
- `htp/pipeline/`
- `htp/solver.py`

## 2. Type, layout, and effect substrate

Implemented today:

- structured scalar dtypes including `i*`, `u*`, `f*`, `bf16`, `bool`
- first-class `index`, symbolic dimensions, and shape payloads
- buffer, tensor, tile, view, token, and channel value kinds
- alias validation for view/buffer relationships
- facet-product layout payload structure
- typed protocol obligations for channels
- schedule directives and legality checks

Main anchors:

- `htp/ir/types.py`
- `htp/ir/layout.py`
- `htp/ir/op_specs.py`
- `htp/passes/program_model.py`
- `htp/passes/typecheck_layout_effects.py`

## 3. Programming surfaces

Implemented today:

- kernel-style program descriptions compiled through `htp.compile_program(...)`
- `htp.compile_program(...)` target support for `pto-*`, `nvgpu-*`, and `aie-*`
- WSP authoring helpers under `htp.wsp`
- CSP authoring helpers under `htp.csp`
- code-backed examples for:
  - PTO vector add
  - NV-GPU GEMM
  - WSP warp GEMM
  - CSP channel pipeline
  - AIE channel pipeline
  - MLIR CSE extension composition
  - serving routine workload

Main anchors:

- `htp/compiler.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/`

## 4. Intrinsics and handlers

Implemented today:

- explicit `IntrinsicDecl`
- portable-vs-backend intrinsic registry queries
- target-specific lower/emit/sim handler availability
- callable `lower` and `emit` dispatch through the registry
- replay stub diagnostic policy per intrinsic
- backend lowering checks through intrinsic-handler declarations
- extension-owned intrinsic package registration (current example: `htp_ext.aie.intrinsics`)

Main anchors:

- `htp/intrinsics.py`
- `htp/runtime/core.py`
- `htp/backends/pto/lower.py`
- `htp/backends/nvgpu/lower.py`

## 5. Passes and pipelines

Implemented today:

- canonical pass management with staged artifacts
- richer staged passes:
  - loop-dependency analysis
  - async/resource analysis
  - schedule analysis/application
  - warp specialization analysis/application
  - software-pipeline analysis/application
- extension-owned pass and pipeline registration
- MLIR CSE island participation in the same framework

Main anchors:

- `htp/passes/manager.py`
- `htp/passes/registry.py`
- `htp/pipeline/registry.py`
- `htp_ext/mlir_cse/island.py`

## 6. Backends, bindings, and runtime integration

Implemented today:

- PTO package emission and real `a2a3sim` execution
- NV-GPU `.cu`-first package emission and real CUDA execution
- AIE extension-owned artifact path plus `compile_program(...)` target support
- AIE planning analyses (`mapping` / `fifo`) staged before MLIR-AIE emission
- normalized binding lifecycle:
  - `validate`
  - `build`
  - `load`
  - `run`
  - `replay`
- structured binding log payloads with schema `htp.binding_log.v1`
- structured adapter trace payloads with schema `htp.adapter_trace.v1`
- replay stub diagnostics that consistently surface `payload_ref`,
  `artifact_ref`, and `fix_hints_ref`
- build/run/replay results that surface `trace_ref` / `trace_refs` from replay
  artifacts or backend adapters
- shared backend artifact contracts consumed by emitters, solver required outputs, and binding path validation

Main anchors:

- `htp/backends/pto/`
- `htp/backends/nvgpu/`
- `htp/backends/declarations.py`
- `htp/bindings/`
- `htp/runtime/errors.py`
- `htp/schemas.py`
- `htp_ext/aie/declarations.py`
- `htp_ext/aie/emit.py`

## 7. Tooling for verification and agent work

Implemented today:

- `htp replay`
- `htp verify`
- `htp promote-plan`
- `htp diff --semantic`
- `htp explain`
- `htp bisect`
- `htp minimize`
- agent policy loading
- promotion recommendation from `agent_policy.toml`
- optional perf threshold checks with package-local metrics
- structured edit-corridor templates for passes, intrinsics, and backend
  contracts in `agent_policy.toml`
- structured diagnostic catalog with exact-code and family-based explanations
- semantic diff evidence that includes compared semantic sidecar refs and
  identity/map refs for staged comparisons
- semantic diff evidence that includes replay-stub refs and `ir/pass_trace.jsonl`
  refs for package-level blame
- agent provenance under `extensions.agent.*`

Main anchors:

- `htp/tools.py`
- `htp/__main__.py`
- `htp/diagnostics.py`
- `htp/agent_policy.py`

## 8. What stays out of this document

Do not use this document for roadmap-only claims.

Remaining work belongs in:

- `docs/future/features.md`
- `docs/future/story.md`
- `docs/future/gap_checklist.md`
