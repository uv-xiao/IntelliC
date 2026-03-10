# TODO — Programming Surfaces

This document tracks the reopened programming-surface work derived from
`docs/design/littlekernel_ast_comparison.md`.

## Why this topic is reopened

The LittleKernel comparison closed one old question — whether HTP understood
the syntax and architecture lessons well enough to apply them. It also exposed
the next concrete surface gaps:

- richer loop / region authoring
- explicit scratch and memory-scope declarations without constructor soup
- stronger workload/dataflow authoring patterns that still read like ordinary
  Python
- continued calibration against the best reference examples rather than only
  minimal compiler demos

Those are concrete future tasks again, so this broad topic is reopened.

## Completion snapshot

- total checklist items: 4
- complete: 0
- partial: 0
- open: 4

## Detailed checklist

### Loop and region authoring
- [ ] Add native loop / region authoring surfaces that remain readable Python and still lower into the canonical HTP program model.

### Scratch and memory-scope authoring
- [ ] Add explicit scratch-buffer / buffer-array / memory-scope declarations on native HTP values so shared-memory and staged-storage examples do not depend on hidden string slots or overly implicit temporaries.

### Workload/dataflow readability
- [ ] Raise WSP and CSP authoring so multi-stage pipelines, role-local steps, and protocol narratives read as complete human programs rather than only thin wrappers around task metadata.

### Reference-calibrated flagship examples
- [ ] Add harder flagship examples calibrated against `references/pypto/`, `references/triton-distributed-knowingnothing/python/little_kernel/`, and `references/arknife/`, and keep using them as the readability bar for public surfaces.

## Coding pointers

- `docs/design/programming_surfaces.md`
- `docs/design/littlekernel_ast_comparison.md`
- `htp/kernel.py`
- `htp/routine.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/`
