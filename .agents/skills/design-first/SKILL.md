---
name: design-first
description: Turn an architectural request into a recorded design before implementation.
---

# Design First

Use this when work changes architecture, compiler representation, APIs, passes, artifacts, or extension seams.

## Workflow

1. Gather context from `docs/story.md`, `docs/design/`, `docs/todo/`, and relevant `docs/notes/`.
2. Record source readings in `docs/notes/` when external documents or repositories affect the design.
3. Present two or three viable approaches with tradeoffs.
4. Select one approach and record it under `docs/in_progress/design/`.
5. Define contracts, invariants, failure modes, and verification evidence.
6. Do not implement until the design has clear acceptance criteria.

## Design Quality Bar

- Explain why the design exists.
- List concrete contracts and owners.
- Include code paths or planned code paths.
- Define how the design will be verified.
- State what is intentionally out of scope.
