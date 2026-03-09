# TODO Layer 2 — Programming Surfaces

This layer tracks the remaining gap between today’s authoring surfaces and the intended Python-native framework.

## Completion snapshot

- total checklist items: 10
- complete: 10
- partial: 0
- open: 0

## Detailed checklist

### Kernel / WSP / CSP authoring
- [x] Provide code-backed WSP authoring.
- [x] Provide code-backed CSP authoring.
- [x] Make flagship authoring patterns look like human-written Python instead of low-level data descriptions where that is still leaking into public examples/tests.
- [x] Broaden the public kernel authoring surface beyond the current proof-oriented entrypoints.
- [x] Integrate an Arknife-style explicit hardware/instruction surface without creating a sidecar compiler path.

### Example quality
- [x] Ship runnable examples across PTO, NV-GPU, WSP, CSP, AIE, MLIR extension composition, and serving routines.
- [x] Replace too-simple flagship examples with harder, reference-calibrated examples that better demonstrate HTP’s intended strengths.
- [x] Raise the public examples to a level that proves richer scheduling/dataflow/backend behavior, not only compact proof cases.

### Serving-routine authoring
- [x] Prove workload-level routine authoring above kernel-only cases.
- [x] Make serving routines a broader first-class public programming surface.

### Comparative analysis
- [x] Finish the written AST-centric comparison against LittleKernel and turn it into the next round of surface requirements.

## Why these tasks remain

This layer is currently closed as a standalone surface gap. The public surface
and examples are materially stronger: PTO examples cover vector add, SwiGLU,
GELU, and a broader arithmetic DAG; WSP/CSP public examples use
decorator/builder authoring instead of direct dict assembly; the
LittleKernel-calibrated WSP and CSP examples carry richer staged intent than a
single `store(C, A @ B)` body; and the completed LittleKernel comparison has
already driven one more surface pass by making staged data-movement and
protocol-style ops return typed temporaries instead of forcing string scratch
names.

Future surface work now belongs to the adjacent semantic and backend layers,
not to a standalone programming-surface comparison gap.

## Coding pointers

Relevant anchors:
- `htp/compiler.py`
- `htp/kernel.py`
- `htp/routine.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `htp/ark/__init__.py`
- `examples/`
- `examples/**/README.md`
- `references/pypto/examples/language/`
- `references/arknife/tests/python/`
- `references/triton-distributed-knowingnothing/python/little_kernel/`
- `docs/design/07_littlekernel_ast_comparison.md`
