# Testing and Verification Rules

## Test Policy

- Add tests for every new contract surface or bug fix.
- Prefer focused regression tests first, then rerun the affected local suite.
- When validation code changes, include malformed-artifact cases, not only happy paths.

## Verification

- Do not claim completion without fresh command output.
- For Python changes, the default verification stack is:
  - `pytest`
  - `pre-commit run --all-files` when hook config changes
- CI should stay small and deterministic:
  - pre-commit on all files
  - pytest on supported Python versions

## Agent Expectations

- Review should look for contract bypasses, malformed-input crashes, and artifact drift.
- Testing should prefer explicit failure diagnostics over implicit exceptions.
