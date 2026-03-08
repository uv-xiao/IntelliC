# Testing and Verification Rules

## Test Policy

- Add tests for every new contract surface or bug fix.
- Prefer focused regression tests first, then rerun the affected local suite.
- When validation code changes, include malformed-artifact cases, not only happy paths.

## Verification

- Do not claim completion without fresh command output.
- For Python changes, the default verification stack is:
  - `pixi run verify`
- Fallback only when Pixi is unavailable:
  - `python -m pip install -e '.[dev]'`
  - `pytest`
  - `pre-commit run --all-files` when hook config changes
- CI should stay small and deterministic:
  - pre-commit through the shared Pixi environment
  - pytest on supported Python versions via named Pixi environments
- A PR is not complete until all configured CI checks are green, not merely locally reproduced.

## Agent Expectations

- Review should look for contract bypasses, malformed-input crashes, and artifact drift.
- Testing should prefer explicit failure diagnostics over implicit exceptions.
