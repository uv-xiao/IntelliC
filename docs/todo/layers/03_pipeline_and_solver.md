# TODO Layer 3 — Pipeline and Solver

This layer tracks the remaining composition work.

## Remaining gaps

- broaden solver search beyond the current deterministic template choice and preflight checks
- deepen `requires` / `provides` reasoning across more pass and extension combinations
- support richer provider composition and resumption from existing package states
- widen MLIR round-trip support beyond the current narrow extension slice
- keep extension islands explicit while broadening the eligible transformed subset

## Visual target

```text
target + requested extensions
            |
            v
      richer solver search
            |
            v
  selected pipeline / extension islands
```

## Why it still matters

The current pipeline discipline is real, but it still proves only a narrow portion of the extensibility story. HTP still needs broader solver power to justify its long-term retargetability claims.
