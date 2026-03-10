# HTP

HTP is a Python-AST-centric compiler framework for heterogeneous tile programs, kernel programs, and workload/dataflow programs.

The repository has three active responsibilities:
- implement the current framework in `htp/` and `htp_ext/`
- document landed behavior in `docs/design/`
- track active feature work through `docs/in_progress/` and reopen `docs/todo/` only when new concrete gaps appear

## Repository status

Implemented today:
- staged replayable compilation artifacts under `ir/stages/`
- shared semantic payloads for kernel/workload/types/layout/effects/schedule
- registry-driven passes, pipeline templates, solver preflight, and machine-visible pass traces
- human-first programming surfaces for kernels, WSP, CSP, and Arknife-style NV-GPU annotation
- MLIR CSE and AIE extension participation
- PTO `a2a3sim` and `a2a3` contracts, NV-GPU CUDA profiling/Blackwell profile plans, AIE reference toolchain paths, and a CPU reference backend
- agent-facing replay, verify, diff, explain, bisect, minimize, promote-plan, policy-check, and workflow-state tooling
- machine-enforced edit-corridor and PR policy checks

Current TODO status:
- `docs/todo/README.md` is fully closed at the moment
- new future work should be reintroduced there only when it is concrete enough to justify a feature PR

## Documentation layout

- `docs/story.md` — final intended framework story
- `docs/design/` — implemented feature documents and code-backed architecture
- `docs/todo/README.md` — current future-work summary, currently closed
- `docs/in_progress/` — active feature-sized PR tasks
- `docs/reference/` — references
- `docs/research/` — research notes and supporting reports

## How to read the docs

Implemented architecture:
- `docs/design/README.md`
- `docs/design/compiler_model.md`
- `docs/design/programming_surfaces.md`
- `docs/design/pipeline_and_solver.md`
- `docs/design/artifacts_replay_debug.md`
- `docs/design/backends_and_extensions.md`
- `docs/design/agent_product_and_workflow.md`
- example-local walkthroughs under `examples/**/README.md`

Supporting analysis:
- `docs/research/retargetable_extensibility_report.md`

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
- `python -m htp policy-check <changed-file> ...`
- `python -m htp workflow-state`

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
1. if there is open future work, choose it from `docs/todo/README.md`
2. create `htp/feat-<topic>`
3. create a task file in `docs/in_progress/` as the first commit
4. open a PR to `htp/dev`
5. implement through more commits
6. before merge, update `docs/design/`, update `docs/todo/README.md` if future-work state changed, and remove the task file from `docs/in_progress/`

Repo-level operating rules live in `AGENTS.md`.
