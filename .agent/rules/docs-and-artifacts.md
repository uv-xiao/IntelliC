# Docs and Artifact Rules

## Documentation structure

- `docs/design/` documents only implemented behavior with references to real code, organized as broad topic docs under `docs/design/`.
- `docs/todo/` holds unimplemented and partial design; `README.md` is authoritative, and detailed feature files appear there only while a concrete future gap is still open.
- `docs/in_progress/` holds active feature-branch task files only.
- `docs/story.md` is the top-level intended framework story.
- Do not leave stale duplicates across these areas.

## Documentation updates

- Update docs when behavior or contracts change.
- Keep docs aligned with current emitted artifact layout and binding behavior.
- Prefer editing the normative existing docs instead of adding ad-hoc markdown.
- When implementation status changes, move docs to the correct area rather than leaving them behind.

## Artifact contracts

- Treat emitted files as stable contracts, not incidental output.
- Canonical paths matter for downstream tooling and verification.
- Schema ids matter; validate them and update docs when they change.
- If a backend emits duplicate metadata surfaces, validation must check their parity.

## Replay and stages

- Every stage should remain runnable in `sim` or fail with a structured replay diagnostic.
- `ir/stages/<id>/program.py` should be readable runnable Python, not only a serialized payload blob.
- Stage identity, maps, analyses, and summaries are part of the observable contract.
