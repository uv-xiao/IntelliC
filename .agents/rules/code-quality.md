# Code Quality Rules

- Write typed, explicit, human-readable code.
- Prefer composition and small modules over deep inheritance and monolithic helpers.
- Avoid stringly semantic ownership when typed ids, typed references, classes, or dataclasses are viable.
- Avoid dict-shaped public APIs unless the dict is an explicit serialization boundary.
- Keep public APIs documented with concise docstrings when names alone do not explain the contract.
- Keep implementation comments focused on invariants, non-obvious decisions, and cross-module contracts.
- Do not add plan-specific comments such as `Phase 1` or `Step 3` inside production code.
- Keep examples and tests readable top-to-bottom; do not hide important state in global payload blobs.
