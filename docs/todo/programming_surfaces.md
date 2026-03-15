# TODO — Programming Surfaces

This document tracks the remaining programming-surface work after the first AST-centric frontend improvements.

## Why this topic remains open

HTP now has a real traced kernel surface, WSP/CSP builders, readable staged Python artifacts, and stronger flagship examples than before. That is not enough yet.

The remaining gap is no longer “can HTP avoid raw payload dicts?” It is more specific:

- can non-trivial mainloops be written as concise Python programs instead of helper choreography?
- can workload/dataflow programs read like authored programs instead of metadata builders?
- can example quality reach the semantic richness of the best PyPTO, LittleKernel, and Arknife references?

The latest surface review distilled those complaints into the checklist below. The review task itself has already been closed and removed from `docs/in_progress/`, so this file is now the source of truth for the remaining frontend work.

## Completion snapshot

- total checklist items: 7
- complete: 4
- partial: 1
- open: 2

## Detailed checklist

### Tile/view and loop-index surface
- [x] Add first-class tile/view slicing on native HTP kernel values so staged copies and tensor-core steps operate on explicit views rather than whole-buffer placeholders.
- [x] Promote loop indices from trace annotations into semantic objects that can participate in view construction, staging, and index-dependent operations.

### WSP authored workload readability
- [x] Add scoped/default schedule contexts so WSP programs do not repeat `.tile(...)`, `.bind(...)`, `.pipeline(...)`, and `.resources(...)` on every task.
- [x] Replace string-only stage markers (`.prologue(...)`, `.steady(...)`, `.epilogue(...)`) with structured or executable task-local authored bodies.

### CSP authored process readability
- [ ] Replace `.compute("name", ...)` as the flagship style with process-local authored bodies built around real `get(...)`, `put(...)`, and compute steps.

### Binding and naming integrity
- [ ] Remove string-tuple argument wiring from flagship WSP/CSP examples by introducing value-based or bind-object-based task/process argument capture.

### Reference-calibrated flagship examples
- [ ] Rebuild the WSP/CSP flagship examples so they match the semantic richness of `references/pypto/`, `references/triton-distributed-knowingnothing/python/little_kernel/`, and `references/arknife/`.

## Recent progress

- high-level compiler / solver / CLI / tool tests now reuse shared authored programs from `tests/programs.py` instead of repeating toy payload dicts
- expression-first kernel authoring landed for arithmetic, temporaries, and staged value flow
- readable staged `program.py` artifacts now remain runnable Python instead of opaque payload dumps
- `htp.kernel` now supports explicit scratch declarations (`scratch(...)`, `scratch_array(...)`, `shared(...)`, `shared_array(...)`, `registers(...)`, `register_array(...)`)
- traced loop/region helpers (`unroll(...)`, `serial(...)`, and `region(...)`) now annotate emitted ops while staying on ordinary Python `for` loops
- the WSP GEMM examples now use explicit scratch arrays, loop/region annotations, and Python-native tile views instead of manually repeated staging code
- WSP workloads now support scoped schedule defaults, bound kernel arguments via `w.args`, and structured stage-body steps instead of only repeated fluent schedule chains and string stage markers

This keeps the topic *partially* closed at the repository level: the frontend is real and testable, but the remaining surface work is now about semantic directness and reference-level readability rather than basic AST tracing.

## Derived PR queue

1. `csp-authored-process-bodies`
2. `value-bound-workload-wiring`
3. `reference-grade-flagship-example-rewrite`

## Coding pointers

- `docs/design/programming_surfaces.md`
- `docs/design/littlekernel_ast_comparison.md`
- `htp/kernel.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/`
- `references/pypto/examples/language/`
- `references/triton-distributed-knowingnothing/python/little_kernel/`
- `references/arknife/tests/python/`
