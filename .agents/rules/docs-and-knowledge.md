# Docs And Knowledge Rules

- `docs/design/` contains implemented behavior only.
- `docs/todo/` contains future or partial work only.
- `docs/in_progress/` contains active feature tasks and active design drafts only.
- `docs/notes/` contains document-reading and repository-reading reports.
- Do not create `docs/reference/` or `docs/research/` in the clean branch.
- Local reading inputs under `.references/` and `.repositories/` remain ignored and uncommitted.
- When an agent reads a substantial document or repository for project decisions, write or update a `docs/notes/` report with source, date, purpose, extracted lessons, and affected decisions.
- Notes are not normative until promoted into `docs/design/`, `docs/todo/`, or `.agents/rules/`.
- Design docs must explain rationale, contracts, code pointers, and verification evidence.
- Do not leave stale duplicates across `docs/design/`, `docs/todo/`, and `docs/in_progress/`.
