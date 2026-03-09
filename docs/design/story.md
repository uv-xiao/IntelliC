# HTP Story — What the Current Repository Proves

This document explains the **implemented** HTP story. It is intentionally narrower than
`docs/future/story.md`: everything here is backed by code in `htp/`, `htp_ext/`, `examples/`,
and `tests/`.

## 1. Repository goal

HTP is a Python-first ML compiler framework for heterogeneous tile programs.

The repository is not just a set of ideas. It already proves a specific architectural claim:

- Python-space remains the canonical compiler form.
- compilation is artifact-first and replayable at every stage,
- solver-visible contracts drive pipeline legality,
- backends consume shared semantic state rather than private compiler sub-architectures,
- and extension mechanisms can participate in the same pipeline without taking semantic ownership
  away from core HTP.

This proof is still incomplete relative to the broader roadmap, but it is real and executable.

## 2. What is already proved

The current implementation proves five things.

### 2.1 Replayable staged compilation

Every compilation produces staged artifacts under `ir/stages/`, including:

- runnable `program.py` replay artifacts,
- staged semantic payloads (`kernel_ir`, `workload_ir`, `types`, `layout`, `effects`, `schedule`),
- staged analyses and pass trace events,
- explicit identity and mapping artifacts when rewrites require them.

The core code paths are:

- `htp/passes/manager.py`
- `htp/passes/trace.py`
- `htp/artifacts/stages.py`
- `htp/runtime/core.py`

### 2.2 Typed semantic substrate

HTP no longer compiles only from ad-hoc dicts or op-name strings. The implemented substrate includes:

- structured scalar, index, shape, buffer, tensor, tile, view, token, and channel payloads,
- explicit op specifications with intrinsic assignment,
- typed layout/effect/schedule payload emission,
- legality checks for dtype support, aliasing, protocol balance, and schedule constraints.

The main anchors are:

- `htp/ir/types.py`
- `htp/ir/layout.py`
- `htp/ir/op_specs.py`
- `htp/passes/program_model.py`
- `htp/passes/typecheck_layout_effects.py`

### 2.3 Solver-visible pipeline composition

HTP now has a real solver/composition layer rather than a single hard-coded pass chain:

- backend capability facts live in backend declarations,
- pass and pipeline registries exist,
- extension templates can participate in solver-visible pipeline choice,
- pass legality is emitted into `ir/pass_trace.jsonl` through `requires_satisfied`.

The core anchors are:

- `htp/solver.py`
- `htp/passes/registry.py`
- `htp/pipeline/registry.py`
- `htp/pipeline/defaults.py`

### 2.4 Real front-end surfaces beyond “kernel only”

The repository now includes code-backed WSP and CSP programming surfaces:

- `htp.wsp` for workload/schedule authoring,
- `htp.csp` for process/channel authoring,
- typed lowering into the shared semantic substrate,
- examples and tests that exercise those surfaces.

See:

- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/wsp_warp_gemm/demo.py`
- `examples/csp_channel_pipeline/demo.py`

### 2.5 Two real execution proofs plus extension participation

The current repository does not stop at package emission.

It includes:

- PTO `a2a3sim` numerical execution through the `pto-runtime` adapter,
- NV-GPU CUDA numerical execution from emitted `.cu` artifacts,
- an extension-owned MLIR round-trip CSE island that participates in the pass/pipeline surface,
- an extension-owned AIE artifact path.

The main anchors are:

- `htp/backends/pto/*`
- `htp/bindings/pto_runtime_adapter.py`
- `htp/backends/nvgpu/*`
- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp_ext/mlir_cse/*`
- `htp_ext/aie/emit.py`

## 3. What this does **not** prove yet

The repository does **not** yet prove the full future story.

Important remaining gaps still live under `docs/future/`:

- richer solver search and cost-driven alternative selection,
- deeper autonomous agent loops and bounded edit policies,
- broader serving-routine programming above the current kernel/workload examples,
- wider backend semantic coverage, especially richer PTO, NV-GPU, and AIE paths,
- broader MLIR island subsets beyond the current implemented round-trip slice.

Use `docs/future/gap_checklist.md` as the authoritative list of remaining gaps.

## 4. How to read the implemented design

Recommended order:

1. `docs/design/README.md`
2. `docs/design/features.md`
3. `docs/design/implementations.md`
4. `docs/design/examples.md`
5. `docs/design/code_map.md`

Then use the deep dives under `docs/design/impls/` for the specific subsystem you are changing.
