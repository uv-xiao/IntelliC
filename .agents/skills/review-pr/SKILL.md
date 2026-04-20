---
name: review-pr
description: Perform a read-only PR or branch review using IntelliC risk and contract checks.
---

# Review PR

Use this for read-only review of a branch or pull request.

## Workflow

1. Resolve the branch or PR.
2. List changed files and classify touched contracts.
3. Consult relevant expert profiles under `.agents/agents/`.
4. Check docs, tests, and policy coverage for the changed contracts.
5. Report findings by severity with file paths, impact, and fix direction.

## Output

Use `.agents/templates/review-report.md`.

## Hard Rules

- Do not edit files.
- Do not change GitHub state.
- Do not run mutating build or install commands during review.
