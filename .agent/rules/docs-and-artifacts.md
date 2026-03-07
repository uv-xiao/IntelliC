# Docs and Artifact Rules

## Documentation

- Update docs when behavior or contracts change.
- Keep docs aligned with the current emitted artifact layout and binding behavior.
- Prefer focused edits to the existing design docs over ad-hoc markdown elsewhere.

## Artifact Contracts

- Treat emitted files as a stable contract, not incidental output.
- Canonical paths matter for downstream tooling and verification.
- Schema ids matter; validate them and update docs when they change.
- If a backend emits duplicate metadata surfaces, validation must check their parity.

## Replay and Stages

- Every stage should remain runnable in `sim` or fail with a structured replay diagnostic.
- Stage identity, maps, analyses, and summaries are part of the observable contract.
