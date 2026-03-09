# HTP

HTP is a Python-first heterogeneous tile compiler framework.

The repository serves two purposes at once:

- it contains the **live implementation** of the current HTP framework in `htp/` and `htp_ext/`
- it contains the **code-backed design documentation** in `docs/design/`

Roadmap and research material that is not fully implemented yet lives under `docs/future/`.

## What the repository already proves

Current code in this branch already provides:

- replayable staged compilation artifacts under `ir/stages/`
- structured semantic payloads for `kernel_ir`, `workload_ir`, `types`, `layout`, `effects`, and `schedule`
- pass contracts, pass traces, and solver preflight with `ir/solver_failure.json`
- registered pass and pipeline surfaces
- WSP and CSP programming surfaces on top of the shared compiler substrate
- staged warp-specialization and software-pipeline passes
- explicit intrinsic declarations and handler availability
- real PTO `a2a3sim` numerical execution
- real NV-GPU CUDA numerical execution from emitted `.cu` artifacts
- an extension-owned MLIR round-trip CSE island
- an extension-owned AIE artifact path
- agent-facing tooling:
  - `htp replay`
  - `htp verify`
  - `htp diff --semantic`
  - `htp explain`
  - `htp bisect`
  - `htp minimize`

This is not the full long-term HTP roadmap. The remaining gaps are tracked in
`docs/future/gap_checklist.md`.

## Repository story

HTP’s current architecture is built around a few explicit rules:

- Python-space remains the canonical compiler form.
- every stage emits replayable artifacts for `sim`
- semantic state is staged explicitly instead of hidden in transient compiler caches
- pass and pipeline legality is solver-visible
- backends consume shared semantic contracts instead of owning separate compiler sub-architectures
- extensions participate through explicit pass, pipeline, and artifact seams

Read:

- `docs/design/story.md`
- `docs/design/features.md`
- `docs/design/implementations.md`
- `docs/design/code_map.md`

## Examples

Runnable examples live under `examples/`:

- `examples/pto_pypto_vector_add/`
- `examples/nvgpu_arknife_gemm/`
- `examples/wsp_warp_gemm/`
- `examples/csp_channel_pipeline/`

Walkthrough docs live under `docs/examples/`.

## Usage

### Python API

Primary entrypoints:

- `htp.compile_program(...)`
- `htp.bind(...)`

### CLI

The repository exposes:

- `python -m htp replay <package>`
- `python -m htp verify <package>`
- `python -m htp diff --semantic <left> <right>`
- `python -m htp explain <diagnostic-code>`
- `python -m htp bisect <left> <right>`
- `python -m htp minimize <package> <output-dir>`

## Development environment

The authoritative development and CI environment is defined by `pixi.toml`.

Preferred commands:

- `pixi run verify`
- `pixi run -e py310 test`
- `pixi run lint`

Fallback path when Pixi is unavailable:

- `python -m pip install -e '.[dev]'`
- `pytest`
- `pre-commit run --all-files`

Runtime dependencies belong in `pyproject.toml` under `[project].dependencies`.
Development-only tools belong in `pixi.toml` and `[project.optional-dependencies].dev`.

## Documentation split

- `docs/design/` = implemented, code-backed behavior only
- `docs/future/` = remaining roadmap, research, and unimplemented design

Use `docs/future/gap_checklist.md` as the operational list of what is still missing.

## Repository workflow

`htp/dev` is the stable branch.

New feature work should go through `htp/feat-*` branches and PR review, with green
verification before merge. The detailed repo contract is in `AGENTS.md`.
