---
name: implement-plan
description: Execute a written implementation plan in small verified batches.
---

# Implement Plan

Use this when a written plan already exists.

## Workflow

1. Read the plan completely.
2. Check for blockers, missing verification, or contradictory steps.
3. Execute one batch at a time.
4. Run the targeted verification for that batch.
5. Commit coherent slices that match the plan.
6. Update task checklists as work lands.
7. Stop if verification fails repeatedly or the plan no longer matches reality.

## Batch Rules

- Do not mix unrelated cleanup with feature work.
- Do not skip verification because a change is “only docs” if a policy test covers docs.
- Keep commits reviewable and reversible.
