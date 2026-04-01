# Core Development Rules

- Treat `htp/dev` as stable and CI-passed.
- Start feature work on `htp/feat-<topic>` branches only.
- Pick features from `docs/todo/README.md`.
- Create a task file under `docs/in_progress/` as the first commit on the branch.
- Keep the canonical compiler form in Python-space.
- Preserve runnable `sim` replay for stage programs.
- Prefer explicit contracts over convention.
- Return structured diagnostics for contract failures.
- Keep changes narrow and local; fix the contract boundary rather than symptoms downstream.
- Do not respond to failures by weakening tests or CI unless the repository contract intentionally changed.
- Use Python 3.10+ idioms and explicit type annotations on public APIs.
- Before merge, move landed behavior into `docs/design/`, update `docs/todo/README.md` plus any active `docs/todo/` feature file if one exists, and remove the corresponding file from `docs/in_progress/`.
- For redesign work, do not keep legacy parallel systems alive after the new
  substrate lands. Temporary migration shims are allowed only within the
  feature branch and must be removed before merge.

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
- WSP examples must show real task roles / dependencies / stage plans, and CSP
  examples must show real process roles / protocol-local steps. If the example
  is only one shallow kernel wrapped in nicer syntax, keep iterating.

## Code readability

- New public modules and public contract-facing APIs must be documented.
- Add comments for invariants and non-obvious decisions, not for obvious lines.
- Prefer explicit, human-readable names.
- In architecture and IR work, avoid stringly-typed refs and dict-shaped
  semantic programming when typed ids, classes, or dataclasses can own the
  contract directly.
- Avoid monolithic procedural code in new substrate work; prefer object-owned
  behavior and explicit extension seams when they improve invariants and
  composability.

## Module organization

- Treat file/module organization as part of the contract in architecture work,
  not as optional cleanup.
- Before adding new logic, identify which module owns:
  - public authoring
  - typed semantics
  - serialization
  - registry/discovery
  - interpretation
  - pass logic
  - artifact emission
- If a file mixes several of those concerns, split it before extending it.
- Do not keep growing a large existing module just because it already exists.
- Keep payload conversion at explicit boundaries; do not scatter payload-shaped
  semantic logic through public surfaces and passes.
