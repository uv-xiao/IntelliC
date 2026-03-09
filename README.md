# HTP

HTP is a Python-AST-centric compiler framework for heterogeneous tile programs, kernel programs, and workload/dataflow programs.

The repository has three simultaneous responsibilities:
- implement the current framework in `htp/` and `htp_ext/`
- document landed behavior in `docs/design/`
- track remaining work and active feature branches through `docs/todo/` and `docs/in_progress/`

## Repository status

What is already real in code:
- replayable staged compilation artifacts under `ir/stages/`
- staged semantic payloads for `kernel_ir`, `workload_ir`, `types`, `layout`, `effects`, and `schedule`
- pass contracts, pass traces, and solver preflight
- WSP and CSP authoring surfaces
- extension participation for MLIR CSE and AIE
- real PTO `a2a3sim` execution
- real NV-GPU CUDA execution
- reference AIE toolchain build and host-runtime path
- agent-facing tooling such as replay, verify, explain, diff, bisect, and minimize

What is not finished yet is tracked under `docs/todo/`.

## Documentation layout

- `docs/story.md` — final intended framework story
- `docs/design/` — implemented, code-backed architecture and features
- `docs/todo/` — remaining features and layered design details for unimplemented work
- `docs/in_progress/` — active feature-branch task files
- `docs/reference/` — reference material
- `docs/research/` — research notes

## Design principles

HTP is built around a few hard constraints:
- Python-space remains the canonical compiler form.
- stage programs remain runnable in `sim` or fail through structured replay diagnostics.
- compiler state is explicit in artifacts rather than hidden in transient pass state.
- backends consume shared semantic contracts instead of owning separate compiler architectures.
- extensions participate through explicit pass, pipeline, and artifact seams.
- agent development is a first-class target, so replay, diagnostics, and emitted schemas must stay stable and inspectable.

## Examples

Runnable code lives under `examples/`.
Implemented walkthroughs live under `docs/design/examples/`.

Examples are intended to demonstrate real functionality, not only smoke cases.
The repository policy is to keep public examples human-readable and Python-native.

## Usage

### Python API

Primary entrypoints:
- `htp.compile_program(...)`
- `htp.bind(...)`

### CLI

- `python -m htp replay <package>`
- `python -m htp verify <package>`
- `python -m htp diff --semantic <left> <right>`
- `python -m htp explain <diagnostic-code>`
- `python -m htp bisect <left> <right>`
- `python -m htp minimize <package> <output-dir>`

## Development environment

The authoritative development and CI environment is `pixi.toml`.

Preferred verification:
- `pixi run verify`

Fallback when Pixi is unavailable:
- `python -m pip install --user --upgrade pip setuptools wheel`
- `python -m pip install -e '.[dev]'`
- `pytest`
- `pre-commit run --all-files`

## Development workflow

`htp/dev` is the stable branch.

Feature development must follow this flow:
1. choose a feature-sized gap from `docs/todo/`
2. create `htp/feat-<topic>`
3. create a task file in `docs/in_progress/` as the first commit
4. open a PR to `htp/dev`
5. implement through additional commits
6. before merge, move landed behavior into `docs/design/`, update `docs/todo/`, and remove the task file from `docs/in_progress/`

Detailed repository rules are in `AGENTS.md`.
