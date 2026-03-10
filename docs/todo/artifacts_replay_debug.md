# TODO — Artifacts, Replay, and Debugging

This document tracks the remaining gap between the current package/debug surface and the final artifact-first framework contract.

## Completion snapshot

- total checklist items: 8
- complete: 7
- partial: 1
- open: 0

## Detailed checklist

### Package and validation surface
- [x] Emit normalized package artifacts, manifests, stage graphs, logs, and sidecars.
- [x] Validate malformed package state through structured diagnostics.
- [x] Broaden generic validation across more backend/extension sidecars and stronger consistency checks.
- [x] Finish the remaining contract/debug uniformity work so every backend and extension path feels equally inspectable.

### Replay and debug surface
- [x] Keep replay distinct from backend package execution.
- [x] Surface replay stubs through structured diagnostics with fix-hint references.
- [~] Broaden replay/reference semantics so fewer boundaries require explicit stubs.
- [x] Keep semantic diff and diagnostic explanation tied to emitted sidecars, ids, maps, and traces.

## Why these tasks remain

This topic is now mostly closed on the package/debug-contract side. PTO,
NV-GPU, and AIE all participate in the same generic sidecar-schema checks, and
invalid sidecars now point back to explicit `artifact_ref` evidence. The only
meaningful remaining gap is replay/reference breadth: reducing how often
backend/extension boundaries still need explicit stubs.

## Coding pointers

Relevant anchors:
- `htp/artifacts/`
- `htp/runtime/`
- `htp/bindings/validate.py`
- `htp/tools.py`
- `htp/diagnostics.py`
- `tests/golden/`
- `tests/tools/`
