# HTP Architecture — Current Implementation

This file documents the architecture that exists in code today. It intentionally
avoids roadmap-only features; those live in `docs/future/`.

## 1. Top-level flow

1. `htp.compile_program(...)` captures a Python-level program description.
2. The capability solver validates the default pipeline and emits `ir/solver_failure.json` on unsat.
3. The default pass pipeline stages runnable Python artifacts under `ir/stages/`.
4. Backend emitters write package-owned sources under `codegen/<backend>/`.
5. Bindings validate, build, load, run, and replay from the emitted package.
6. Agent-facing tools consume artifact packages through replay/verify/diff/explain.

Implementation anchors:

- compiler entrypoint: `htp/compiler.py`
- solver: `htp/solver.py`
- default pipeline: `htp/pipeline/defaults.py`
- pass manager: `htp/passes/manager.py`
- manifest emission: `htp/artifacts/manifest.py`
- binding selection: `htp/bindings/api.py`
- tool API / CLI: `htp/tools.py`, `htp/__main__.py`

## 2. Canonical representation

The canonical compiler form is staged Python-space state plus emitted replay
programs.

- identity and maps live in `htp/ir/`
- typed semantic state lives in `htp/ir/semantics.py`
- op registry and semantic broadening live in `htp/ir/op_specs.py`
- every stage emits `program.py` for `sim` replay
- every stage also emits semantic payloads (`kernel_ir.json`, `workload_ir.json`,
  `types.json`, `layout.json`, `effects.json`, `schedule.json`)
- analyses are emitted as artifacts alongside the stage program
- island metadata can be emitted directly from pass results

See `docs/design/impls/01_ir_model.md` and `docs/design/impls/02_pass_manager.md`.

## 3. Pass spine

The default pipeline today is:

1. `ast_canonicalize`
2. `semantic_model`
3. `typecheck_layout_effects`
4. `analyze_schedule`
5. `apply_schedule`
6. `emit_package`

These passes live in `htp/passes/` and emit:

- `ir/pass_trace.jsonl`
- `ir/stages/<id>/program.py`
- `ir/stages/<id>/program.pyast.json`
- `ir/stages/<id>/kernel_ir.json`
- `ir/stages/<id>/workload_ir.json`
- `ir/stages/<id>/types.json`
- `ir/stages/<id>/layout.json`
- `ir/stages/<id>/effects.json`
- `ir/stages/<id>/schedule.json`
- `ir/stages/<id>/analysis/index.json`
- `ir/stages/<id>/ids/*.json`
- `ir/stages/<id>/summary.json`

## 4. Artifact contract

Every compiled package contains:

- `manifest.json`
- staged IR under `ir/stages/`
- backend-owned sources under `codegen/<backend>/`
- build metadata under `build/`
- logs written by bindings under `logs/`

The normative schemas and validators live in:

- `htp/schemas.py`
- `htp/artifacts/manifest.py`
- `htp/artifacts/validate.py`
- `docs/design/impls/04_artifact_manifest.md`

## 5. Backends

### PTO

- lowerer: `htp/backends/pto/lower.py`
- emitter: `htp/backends/pto/emit.py`
- binding: `htp/bindings/pto.py`
- runtime adapter: `htp/bindings/pto_runtime_adapter.py`

HTP emits a PTO package and delegates real build/run work to the local
`pto-runtime` checkout, preferring `3rdparty/pto-runtime/` and falling back to
`references/pto-runtime/`. The current implemented example path is a numerically
validated `a2a3sim` vector add over marshaled `numpy.float32` buffers.

### NV-GPU

- lowerer: `htp/backends/nvgpu/lower.py`
- emitter: `htp/backends/nvgpu/emit.py`
- binding: `htp/bindings/nvgpu.py`
- CUDA adapter: `htp/bindings/nvgpu_cuda_adapter.py`

HTP owns `.cu` source artifacts; the binding owns `nvcc` materialization and
CUDA-driver launch. The current implemented example path is a real GEMM kernel
running on CUDA with explicit tensor/scalar arguments.

### AIE extension backend

- emitter: `htp_ext/aie/emit.py`
- binding: `htp/bindings/aie.py`

HTP now has an extension-owned MLIR-AIE artifact path. It emits `codegen/aie/`
artifacts plus `extensions.aie.*` metadata and keeps replay in Python `sim`.

## 6. Replay versus backend execution

HTP keeps two execution surfaces distinct:

- replay: `ir/stages/<id>/program.py` through `htp/runtime/`
- package execution: backend-owned build/load/run through `htp/bindings/`

This distinction is part of the public contract and is documented in
`docs/design/impls/07_binding_interface.md`.

## 7. Extension boundary

The only extension package in tree today is:

- `htp_ext/mlir_cse/`
- `htp_ext/aie/`

Implemented extension-owned seams now include:

- MLIR CSE round-trip package emission with solver-visible eligibility
- AIE artifact emission with binding validation

Anything not backed by code in `htp/` or `htp_ext/` remains future work.
