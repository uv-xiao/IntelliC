# Testing and Verification Rules

## Test policy

- Add tests for every new contract surface or bug fix.
- Prefer focused regression tests first, then rerun the affected local suite.
- When validation code changes, include malformed-artifact cases, not only happy paths.
- Do not add redundant, low-signal, or trivially duplicative tests just to increase test count.
- Prefer tests that defend a contract boundary, failure mode, or previously observed regression.
- Be able to justify each new test in one sentence: what bug or contract does it protect?
- If several tests cover the same path with no new signal, collapse them.

## Example quality

- Public examples are part of the proof surface and must be human-friendly.
- Prefer Python-native authoring and readable builders over giant raw dict globals.
- Use references and real systems to calibrate example difficulty.
- Flagship examples should demonstrate real functionality, not only a minimal smoke case.
- Use `references/pypto/` and `references/arknife/` as the baseline when
  judging whether a flagship example is too small or too mechanical.

## Verification

- Do not claim completion without fresh command output.
- Default verification stack:
  - `pixi run verify`
- Fallback only when Pixi is unavailable:
  - `python -m pip install --user --upgrade pip setuptools wheel`
  - `python -m pip install -e '.[dev]'`
  - `pytest`
  - `pre-commit run --all-files`
- A PR is not complete until all configured CI checks are green.
- Do not fix CI by deleting coverage, loosening assertions, skipping real failure paths, or removing jobs unless the underlying contract intentionally changed and the docs/tests were updated consistently.
- When CI fails, first investigate whether the failure reveals a real defect in code, fixtures, dependencies, or environment handling.
