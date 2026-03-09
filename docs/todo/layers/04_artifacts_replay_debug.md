# TODO Layer 4 — Artifacts, Replay, and Debugging

This layer tracks the remaining gap between the current package/debug surface and the final artifact-first framework contract.

## Completion snapshot

- total checklist items: 8
- complete: 5
- partial: 2
- open: 1

## Detailed checklist

### Package and validation surface
- [x] Emit normalized package artifacts, manifests, stage graphs, logs, and sidecars.
- [x] Validate malformed package state through structured diagnostics.
- [~] Broaden generic validation across more backend/extension sidecars and stronger consistency checks.
- [ ] Finish the remaining contract/debug uniformity work so every backend and extension path feels equally inspectable.

### Replay and debug surface
- [x] Keep replay distinct from backend package execution.
- [x] Surface replay stubs through structured diagnostics with fix-hint references.
- [~] Broaden replay/reference semantics so fewer boundaries require explicit stubs.
- [x] Keep semantic diff and diagnostic explanation tied to emitted sidecars, ids, maps, and traces.

## Why these tasks remain

This layer is already one of the strongest parts of the repository. The remaining work is mostly consistency and breadth: making all backend and extension paths live up to the same artifact/debug standard.

## Coding pointers

Relevant anchors:
- `htp/artifacts/`
- `htp/runtime/`
- `htp/bindings/validate.py`
- `htp/tools.py`
- `htp/diagnostics.py`
- `tests/golden/`
- `tests/tools/`
