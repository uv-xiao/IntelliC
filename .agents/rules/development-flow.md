# Development Flow Rules

- Work on feature-sized branches, not directly on stable release branches.
- Start feature work from the current designated base branch.
- Pick or create a feature-sized gap in `docs/todo/README.md`.
- Create a task file under `docs/in_progress/` before implementation.
- Architecture-changing work must create design drafts under `docs/in_progress/design/` before implementation.
- Multi-file work requires a written plan with explicit input, output, and verification criteria.
- Before merge, move implemented design into `docs/design/`, update `docs/todo/`, remove stale task files, and remove completed `docs/in_progress/design/` drafts.
- Do not preserve legacy parallel systems after a redesign supersedes them.
- Commit in coherent slices that match the task plan.
