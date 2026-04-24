---
name: merge-pr
description: Merge or finalize an IntelliC pull request, including archiving closed-PR human_words records under docs/archive with a PR-derived name.
---

# Merge PR

Use this when merging a PR, immediately after a PR has been merged, or when cleaning up documentation for a closed PR.

## Workflow

1. Identify the PR number and title from the merge commit, squash commit subject, GitHub PR metadata, or the user's explicit wording.
2. Generate an archive slug:
   - Prefer `pr-<number>-<title-slug>` when a PR number is known.
   - Otherwise use `<branch-or-feature-slug>-<date>` if no PR number is available.
   - Use lowercase ASCII, hyphens, and enough title words to identify the PR.
3. If `docs/in_progress/human_words/` contains records for that PR, move the directory contents to `docs/archive/<archive-slug>/human_words/`.
4. Recreate `docs/in_progress/human_words/README.md` for future active work.
5. Keep `docs/archive/<archive-slug>/README.md` brief: name the PR, source commit or branch when known, and explain that the archived `human_words/` records are preserved historical source wording.
6. Verify with `find docs/archive/<archive-slug> docs/in_progress/human_words -maxdepth 2 -type f | sort` and a focused reread of the active and archived README files.

## Guardrails

- Do not delete human wording when archiving. Move it or copy it only when move is impossible.
- Do not leave completed PR human wording in `docs/in_progress/human_words/`.
- Do not archive active work for another open PR into the closed PR folder.
