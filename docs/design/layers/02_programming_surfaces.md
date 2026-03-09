# Layer 2 — Programming Surfaces

This layer describes how users currently express programs for HTP and how those surfaces converge on the shared semantic core.

## Why this layer exists

HTP is Python-AST-centric. That should mean more than “the compiler happens to store Python AST internally”. It should mean that user-facing programs are readable, inspectable Python programs and that WSP/CSP are frontend surfaces over the same compiler, not separate semantic silos.

The implemented repository proves that convergence at a limited but real scale.

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

## Implemented surfaces

### `htp.compile_program(...)`

The generic compilation entrypoint already supports:
- PTO targets
- NV-GPU targets
- AIE extension targets

It captures package-level metadata, invokes solver + pipeline selection, emits staged artifacts, and hands the result to bindings and tool surfaces.

### WSP

`htp.wsp` is now a real code-backed frontend surface rather than a pure design note. It proves that workload/schedule authoring can be expressed explicitly and then lowered into the shared semantic substrate instead of creating a new compiler path.

The current proof points include:
- staged scheduling evidence
- warp-role planning
- software-pipeline planning
- shared lowering through the same pass manager and artifact model

### CSP

`htp.csp` now proves that process/channel authoring can live inside the same compiler architecture. Current CSP examples and tests show:
- typed channels
- protocol obligations
- deadlock/progress evidence
- lowering into shared workload/effect state

### Workload-level routines

The repository also includes a workload-level serving routine example, which matters because HTP is not meant to stop at kernels only.

## Implemented feature inventory

Code-backed example families currently include:
- PTO vector add
- NV-GPU GEMM
- WSP warp GEMM
- CSP channel pipeline
- AIE channel pipeline
- MLIR CSE extension composition
- serving routine workload

These examples are important because they are the public proof surface for the framework. They show which authoring claims are real today.

## Rationale for the current split

HTP deliberately separates:
- the authoring surface a user touches,
- from the semantic state the compiler stages,
- from the backend package the binding executes.

That separation is what allows one frontend surface to target multiple backends without each backend becoming the semantic owner.

## Coding pointers

If you are working in this layer, start here:
- `htp/compiler.py` — generic program compilation entrypoint
- `htp/wsp/__init__.py` — WSP authoring helpers
- `htp/csp/__init__.py` — CSP authoring helpers
- `examples/` — runnable proof surface
- `docs/design/examples/` — narrative walkthroughs tied to those examples

If the work changes what “good” public authoring looks like, update both the code examples and the example docs.

## Current limits

The user-facing surfaces are still narrower and more mechanical than the final intended framework. The missing work now lives in `docs/todo/layers/02_programming_surfaces.md`.
