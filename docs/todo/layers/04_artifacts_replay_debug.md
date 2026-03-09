# TODO Layer 4 — Artifacts, Replay, and Debugging

This layer tracks remaining package-contract and debug work.

## Remaining gaps

- add deeper generic validation across more backend and extension sidecars
- improve binding and extension consistency checks where contracts still rely on narrow assumptions
- broaden semantic diff and debug guidance beyond the current implemented evidence set
- deepen replay/reference semantics so fewer boundaries require explicit stubs
- keep documentation and package contracts synchronized as broader feature work lands

## Visual target

```text
compile -> package -> replay / verify / diff / explain
                    \-> richer contract validation
```

## Why it still matters

Retargetability and agent-friendliness depend on artifact discipline. The current substrate is strong, but the future framework still needs a broader and more uniform contract/debug surface.
