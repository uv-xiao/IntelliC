# HTP Testing

Use this when validating HTP changes.

## Default Commands

- `pytest`
- `pre-commit run --all-files`

## Priorities

1. Run the smallest failing regression first.
2. Re-run the affected subsystem tests.
3. Re-run the broader suite if scaffolding or shared contract code changed.

## Required Checks

- schema validation failures are diagnosed cleanly,
- malformed artifacts do not crash validators,
- backend selection cannot bypass backend-specific contract checks.
