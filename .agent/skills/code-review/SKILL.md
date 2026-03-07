# HTP Code Review

Use this when reviewing HTP changes.

## Focus

- contract completeness,
- malformed-input robustness,
- replay and artifact invariants,
- binding/backend parity across duplicated metadata.

## Review Questions

- Can malformed manifests or artifacts crash instead of returning diagnostics?
- Can a backend-specific package bypass its binding validation path?
- Do emitted artifacts, manifest metadata, and toolchain pins agree?
- Do tests cover both happy path and corruption path?
