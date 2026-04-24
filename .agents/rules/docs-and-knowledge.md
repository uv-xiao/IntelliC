# Docs And Knowledge Rules

- `docs/design/` contains accepted architecture and implemented behavior only.
- `docs/todo/` contains future or partial work only.
- `docs/in_progress/` contains active feature tasks and active design drafts only.
- `docs/archive/` contains closed-PR historical artifacts that should be preserved but are no longer active.
- Record human instructions under `docs/in_progress/human_words/` during active
  work. Preserve the user's wording, date, and context; promote only curated
  decisions into rules, tasks, or design docs.
- When merging a PR, move that PR's `docs/in_progress/human_words/` contents
  into `docs/archive/<pr-number-or-slug>-<pr-title-slug>/human_words/`, then
  recreate an empty active `docs/in_progress/human_words/` area for future work.
- `docs/notes/` contains document-reading and repository-reading reports.
- Do not create `docs/reference/` or `docs/research/` in the clean branch.
- Local reading inputs under `.references/` and `.repositories/` remain ignored and uncommitted.
- When an agent reads a substantial document or repository for project decisions, write or update a `docs/notes/` report with source, date, purpose, source scope, diagrams or flowcharts for structure/process, code or schema sketches for API/implementation evidence, comparison tables when sources are weighed, extracted lessons, affected decisions, and follow-up verification evidence.
- `docs/notes/` reports must not be summary-only when the source affects design, rules, tasks, or implementation direction.
- Notes are not normative until promoted into `docs/design/`, `docs/todo/`, or `.agents/rules/`.
- Design docs must explain rationale, contracts, code pointers, and verification evidence.
- Documentation-only changes do not need automated tests; verify them with
  reading, link/path checks, policy checks, or rendered-doc inspection as
  appropriate.
- Do not leave stale duplicates across `docs/design/`, `docs/todo/`, and `docs/in_progress/`.
