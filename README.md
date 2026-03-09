# HTP

HTP is a Python-AST-centric compiler framework for heterogeneous tile programs, kernel programs, and workload/dataflow programs.

The repository has three active responsibilities:
- implement the current framework in `htp/` and `htp_ext/`
- document landed behavior in `docs/design/`
- track remaining and active feature work through `docs/todo/` and `docs/in_progress/`

## Repository status

Implemented today:
- staged replayable compilation artifacts under `ir/stages/`
- shared semantic payloads for kernel/workload/types/layout/effects/schedule
- registry-driven passes, pipeline templates, and solver preflight
- WSP and CSP authoring surfaces
- MLIR CSE and AIE extension participation
- PTO `a2a3sim`, NV-GPU CUDA, and AIE reference toolchain paths
- agent-facing replay, verify, diff, explain, bisect, minimize, and promote-plan tooling

Not finished yet:
- broader semantic breadth, richer programming surfaces, deeper solver behavior, broader backend coverage, and fuller agent loops
- the authoritative remaining work lives in `docs/todo/`

## Documentation layout

- `docs/story.md` — final intended framework story
- `docs/design/` — implemented layers, examples, and code-backed architecture
- `docs/todo/` — remaining layers and future work
- `docs/in_progress/` — active feature-sized PR tasks
- `docs/reference/` — references
- `docs/research/` — research notes

## How to read the docs

Implemented architecture:
- `docs/design/README.md`
- `docs/design/layers/01_compiler_model.md`
- `docs/design/layers/02_programming_surfaces.md`
- `docs/design/layers/03_pipeline_and_solver.md`
- `docs/design/layers/04_artifacts_replay_debug.md`
- `docs/design/layers/05_backends_and_extensions.md`
- `docs/design/layers/06_agent_product_and_workflow.md`
- `docs/design/examples/README.md`

Remaining work:
- `docs/todo/README.md`
- `docs/todo/layers/`
- `docs/todo/reports/retargetable_extensibility_report.md`

## Usage

Primary Python entrypoints:
- `htp.compile_program(...)`
- `htp.bind(...)`

CLI surface:
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

Feature work must follow this loop:
1. choose a feature-sized gap from `docs/todo/`
2. create `htp/feat-<topic>`
3. create a task file in `docs/in_progress/` as the first commit
4. open a PR to `htp/dev`
5. implement through more commits
6. before merge, update `docs/design/`, update `docs/todo/`, and remove the task file from `docs/in_progress/`

Repo-level operating rules live in `AGENTS.md`.
