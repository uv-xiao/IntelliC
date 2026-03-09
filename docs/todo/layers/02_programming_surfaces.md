# TODO Layer 2 — Programming Surfaces

This layer tracks the remaining gap between today’s authoring surfaces and the intended Python-native framework.

## Completion snapshot

- total checklist items: 9
- complete: 8
- partial: 0
- open: 1

## Detailed checklist

### Kernel / WSP / CSP authoring
- [x] Provide code-backed WSP authoring.
- [x] Provide code-backed CSP authoring.
- [x] Make flagship authoring patterns look like human-written Python instead of low-level data descriptions where that is still leaking into public examples/tests.
- [x] Broaden the public kernel authoring surface beyond the current proof-oriented entrypoints.

### Example quality
- [x] Ship runnable examples across PTO, NV-GPU, WSP, CSP, AIE, MLIR extension composition, and serving routines.
- [x] Replace too-simple flagship examples with harder, reference-calibrated examples that better demonstrate HTP’s intended strengths.
- [x] Raise the public examples to a level that proves richer scheduling/dataflow/backend behavior, not only compact proof cases.

### Serving-routine authoring
- [x] Prove workload-level routine authoring above kernel-only cases.
- [x] Make serving routines a broader first-class public programming surface.

### Comparative analysis
- [ ] Finish the written AST-centric comparison against LittleKernel and turn it into the next round of surface requirements.

## Why these tasks remain

The public surface and examples are now materially stronger: PTO examples cover
vector add, SwiGLU, GELU, and a broader arithmetic DAG; WSP/CSP public examples
no longer depend on nested top-level payload dicts; and a LittleKernel-inspired
WSP example now exists. The remaining gap in this layer is no longer “make the
surface readable at all”. It is the written comparative analysis tracked in
`docs/todo/reports/littlekernel_ast_comparison.md`, which should drive the next
front-end pass.

## Coding pointers

Relevant anchors:
- `htp/compiler.py`
- `htp/kernel.py`
- `htp/routine.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/`
- `docs/design/examples/`
- `references/pypto/examples/language/`
- `references/arknife/tests/python/`
- `references/triton-distributed-knowingnothing/python/little_kernel/`
- `docs/todo/reports/littlekernel_ast_comparison.md`
