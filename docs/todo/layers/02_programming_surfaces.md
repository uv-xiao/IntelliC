# TODO Layer 2 — Programming Surfaces

This layer tracks the remaining gap between the current authoring surfaces and the final intended Python-native framework.

## Remaining gaps

- make user-facing program authoring more Python-native and less dependent on low-level dict-shaped kernels outside contract tests
- broaden WSP and CSP surfaces from proof examples into richer public programming models
- deepen serving-routine authoring so orchestration/dataflow above kernels is a real first-class user surface
- replace too-simple flagship examples with harder, reference-calibrated examples across backends

## Visual target

```text
human Python
  |-- kernels
  |-- WSP
  |-- CSP
  `-- serving routines
```

## Why it still matters

HTP’s claim is not just that Python AST is the canonical compiler form; it is that humans should be able to author programs naturally in Python and still get explicit staged compiler evidence. That user experience is still incomplete.
