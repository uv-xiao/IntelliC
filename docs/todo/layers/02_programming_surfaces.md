# TODO Layer 2 — Programming Surfaces

This layer tracks the remaining gap between today’s authoring surfaces and the intended Python-native framework.

## Completion snapshot

- total checklist items: 8
- complete: 4
- partial: 2
- open: 2

## Detailed checklist

### Kernel / WSP / CSP authoring
- [x] Provide code-backed WSP authoring.
- [x] Provide code-backed CSP authoring.
- [~] Make flagship authoring patterns look like human-written Python instead of low-level data descriptions where that is still leaking into public examples/tests.
- [ ] Broaden the public kernel authoring surface beyond the current proof-oriented entrypoints.

### Example quality
- [x] Ship runnable examples across PTO, NV-GPU, WSP, CSP, AIE, MLIR extension composition, and serving routines.
- [~] Replace too-simple flagship examples with harder, reference-calibrated examples that better demonstrate HTP’s intended strengths.
- [ ] Raise the public examples to a level that proves richer scheduling/dataflow/backend behavior, not only compact proof cases.

### Serving-routine authoring
- [x] Prove workload-level routine authoring above kernel-only cases.
- [ ] Make serving routines a broader first-class public programming surface.

## Why these tasks remain

The surfaces are real, but they still look more like proof scaffolding than the final public programming experience. The remaining work is about authoring quality, example difficulty, and richer orchestration surfaces.

## Coding pointers

Relevant anchors:
- `htp/compiler.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/`
- `docs/design/examples/`
