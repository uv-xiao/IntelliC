# HTP Design

`docs/design/` is the normative description of what is implemented in this repository.

Everything here must be backed by code in `htp/`, `htp_ext/`, `examples/`, and tests.
Unimplemented ideas belong in `docs/todo/`, not here.

## Read order

- `docs/story.md` — final goal and full intended framework story
- `docs/design/README.md` — implemented architecture index
- `docs/design/story.md` — current code-backed claim
- `docs/design/features.md` — implemented feature surface by layer
- `docs/design/implementations.md` — implemented architecture and contracts
- `docs/design/code_map.md` — path from design docs to real code
- `docs/design/examples.md` — implemented example flows and proof points

## Implemented layer docs

### Core compiler layers
- `docs/design/impls/01_ir_model.md`
- `docs/design/impls/02_pass_manager.md`
- `docs/design/impls/03_capability_solver.md`
- `docs/design/impls/04_artifact_manifest.md`
- `docs/design/impls/07_binding_interface.md`
- `docs/design/impls/08_testing.md`
- `docs/design/impls/09_debuggability.md`
- `docs/design/impls/10_agentic_tooling.md`

### Backend and extension layers
- `docs/design/impls/05_backend_pto.md`
- `docs/design/impls/06_backend_aie.md`
- `docs/design/impls/12_mlir_roundtrip_island.md`
- `docs/design/impls/13_backend_nvgpu.md`

### Case-study layers
- `docs/design/impls/11_warp_specialization_pipelining.md`

## Implemented example docs

- `docs/design/examples/README.md`
- `docs/design/examples/pto_pypto_vector_add.md`
- `docs/design/examples/nvgpu_arknife_gemm.md`
- `docs/design/examples/wsp_warp_gemm.md`
- `docs/design/examples/csp_channel_pipeline.md`
- `docs/design/examples/aie_channel_pipeline.md`
- `docs/design/examples/mlir_cse_extension.md`
- `docs/design/examples/serving_routine.md`

## What is not here

- unimplemented roadmap items → `docs/todo/`
- active feature tasks → `docs/in_progress/`
- references and research corpora → `docs/reference/`, `docs/research/`
