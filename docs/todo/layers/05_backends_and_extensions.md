# TODO Layer 5 — Backends and Extensions

This layer tracks remaining backend depth and breadth.

## Remaining gaps

- broaden PTO beyond the current `a2a3sim`-anchored path into richer orchestration and device coverage
- deepen NV-GPU lowering, runtime breadth, profiling, and Blackwell-specialized behavior
- deepen AIE beyond the current reference planning/emission/build/run path
- optionally add another extension backend only if it strengthens the shared-substrate claim
- keep all backend growth tied to shared semantic contracts rather than backend-local compiler forks

## Visual target

```text
shared semantics
   |        |        |      (+ future extension)
   v        v        v
 PTO      NVGPU     AIE
```

## Why it still matters

The current backends are real proofs, but they do not yet exhaust the target retargetability story. The missing work is backend depth, not a new architecture.
