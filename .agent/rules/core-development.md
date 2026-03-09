# Core Development Rules

- Treat `htp/dev` as stable and CI-passed.
- Start feature work on `htp/feat-<topic>` branches only.
- Pick features from `docs/todo/README.md` and the layer docs under `docs/todo/`.
- Create a task file under `docs/in_progress/` as the first commit on the branch.
- Keep the canonical compiler form in Python-space.
- Preserve runnable `sim` replay for stage programs.
- Prefer explicit contracts over convention.
- Return structured diagnostics for contract failures.
- Keep changes narrow and local; fix the contract boundary rather than symptoms downstream.
- Do not respond to failures by weakening tests or CI unless the repository contract intentionally changed.
- Use Python 3.10+ idioms and explicit type annotations on public APIs.
- Before merge, move landed behavior into `docs/design/`, update `docs/todo/README.md` plus the affected `docs/todo/*.md`, and remove the corresponding file from `docs/in_progress/`.

## Example and test authoring

- Public examples and high-level tests must read like native Python programs.
- Do not use large top-level raw-data program blobs for flagship examples.
- Prefer decorator-based or traced authoring surfaces over spec-constructor
  call stacks in public examples.
- Use raw dict payloads only for low-level contract tests.
- Flagship examples must be substantial enough to demonstrate a real compiler capability, not only a smoke path.
- Review programming surfaces and public examples for human friendliness and
  syntax prettiness explicitly; technically correct but awkward authoring does
  not clear the quality bar.

## Code readability

- New public modules and public contract-facing APIs must be documented.
- Add comments for invariants and non-obvious decisions, not for obvious lines.
- Prefer explicit, human-readable names.
