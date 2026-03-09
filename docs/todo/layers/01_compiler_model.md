# TODO Layer 1 — Compiler Model, Semantics, and Typing

This layer tracks what is still missing from the final semantic core.

## Remaining gaps

- broaden the shared semantic operation set beyond the current implemented surface
- deepen the user-facing type system so it is not only an internal staged payload model
- expand layout algebra beyond the current implemented facet payloads and conservative legality rules
- broaden collective, protocol, and async semantics across more backend discharge paths
- make richer serving-routine semantics first-class rather than mostly example-level

## Visual target

```text
Python program
    |
    +-- executable stage program
    +-- full semantic model
    +-- full type/layout/effect algebra
```

## Why it still matters

The current substrate is real, but still not broad enough to claim the full target envelope in `docs/story.md`. HTP still needs a richer semantic core so backends and extension pipelines can rely on one shared model rather than ad-hoc front-end conventions.
