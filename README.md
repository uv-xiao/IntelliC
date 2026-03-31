# HTP

HTP is a Python-AST-centric compiler framework for heterogeneous tile programs, kernel programs, and workload/dataflow programs.

Its primary goal is not only retargetability. It is to build a compiler stack
that is both human-friendly and LLM-friendly, with AST all the way as the core
discipline.

The repository has three active responsibilities:
- implement the current framework in `htp/` and `htp_ext/`
- document landed behavior in `docs/design/`
- track active feature work through `docs/in_progress/` and reopen `docs/todo/` only when new concrete gaps appear

That top-level goal has two strict consequences:

- human-friendly: intermediate compiler artifacts must still unparse into
  readable native Python that a person can inspect and edit
- LLM-friendly: mutated intermediate artifacts must still unparse into runnable
  Python with an executor/interpreter path so tools and agents can replay them

## Repository status

Implemented today:
- staged replayable compilation artifacts under `ir/stages/`
- compact staged state bundles rooted at `program.py`, `stage.json`, and `state.json`
- `ProgramModule`-first lowering from the current public frontend set (`kernel`,
  `routine`, `wsp`, and `csp`)
- registry-driven passes, pipeline templates, solver preflight, and machine-visible pass traces
- human-first programming surfaces for kernels, WSP, CSP, and Arknife-style NV-GPU annotation
- MLIR CSE and AIE extension participation
- PTO `a2a3sim` and `a2a3` contracts, NV-GPU CUDA profiling/Blackwell profile plans, AIE reference toolchain paths, and a CPU reference backend
- agent-facing replay, verify, diff, explain, bisect, minimize, promote-plan, policy-check, and workflow-state tooling
- machine-enforced edit-corridor and PR policy checks

Current TODO status:
- `docs/todo/README.md` is authoritative for future work
- the currently reopened topic is `docs/todo/alignment_and_product_gaps.md`
- the remaining open work is now mainly:
  - programming-surface quality,
  - flagship example realism,
  - backend-depth widening,
  - and keeping top-level docs/status claims honest

## Documentation layout

- `docs/story.md` — final intended framework story
- `docs/design/` — implemented feature documents and code-backed architecture
- `docs/todo/README.md` — current future-work summary
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
- `docs/design/status_and_alignment.md`
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
