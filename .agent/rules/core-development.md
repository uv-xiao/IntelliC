# Core Development Rules

## Scope

These are the base rules for HTP development.

## Rules

- Treat `htp/dev` as stable and CI-passed.
- Start new feature work on `htp/feat-<topic>` branches and merge back through a PR-style review step.
- Keep the canonical compiler form in Python-space; do not introduce hidden semantic owners outside the staged artifact model.
- Preserve runnable `sim` replay as the default invariant for stage programs.
- Prefer explicit contracts over convention:
  - manifest fields,
  - staged artifact paths,
  - binding diagnostics,
  - backend extension surfaces.
- Return structured diagnostics for contract failures; do not let malformed package state crash validation paths.
- Keep changes narrow and local; fix the contract boundary rather than patching symptoms downstream.
- Use Python 3.10+ idioms and explicit type annotations on public APIs.
- Avoid hidden global state for compilation or binding behavior.

## Non-Goals

- Do not add broad infrastructure copied from other repos unless HTP actually uses it.
- Do not add agent-only abstractions that are not tied to replay, artifacts, bindings, or backend contracts.
- Do not use `htp/dev` as a scratch branch for in-progress feature work.
