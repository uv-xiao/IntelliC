# Layer 2 — Programming Surfaces

This layer describes how users currently express programs for HTP.

## Narrative

HTP is Python-AST-centric, so the intended public programming model is native Python authoring rather than raw serialized program blobs. The current repository implements three code-backed authoring surfaces:
- kernel/workload programs passed to `htp.compile_program(...)`
- WSP helpers under `htp.wsp`
- CSP helpers under `htp.csp`

These are not separate compiler worlds. They lower into the same shared semantic substrate described in Layer 1.

What is already real:
- kernel-style program descriptions for PTO, NV-GPU, and AIE targets
- WSP schedule-oriented examples that emit staged scheduling evidence
- CSP process/channel examples that emit typed protocol and effect evidence
- workload-level serving routine examples above simple kernel-only paths

## Visual model

```text
Python authoring
   |-- compile_program(...)
   |-- htp.wsp
   `-- htp.csp
            |
            v
 shared kernel/workload semantics
```

## Implemented contracts

- WSP and CSP are frontend surfaces over the shared compiler substrate, not separate compilers
- flagship examples must be human-readable and Python-native
- example docs in `docs/design/examples/` are tied directly to runnable code under `examples/`

## Main code anchors

- `htp/compiler.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/`
