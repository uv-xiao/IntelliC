---
name: create-pr
description: Prepare and publish an IntelliC pull request after local verification.
---

# Create PR

Use this when publishing a feature branch.

## Workflow

1. Confirm the current branch is not the stable base branch.
2. Confirm `git status --short` is clean or intentionally staged.
3. Run the relevant verification skill.
4. Ensure `docs/design/`, `docs/todo/`, and `docs/in_progress/` are consistent with branch state.
5. Write a PR body using `.agents/templates/pr-body.md`.
6. Push the branch and create or update the PR.

## Guardrails

- Never force-push without explicit user approval.
- Never publish with stale completed design drafts under `docs/in_progress/design/`.
- Never include AI co-author lines.
