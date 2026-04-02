# Foundations

## Goal

HTP's primary goal is to build a compiler stack that is both human-friendly and
LLM-friendly.

- human-friendly means intermediate artifacts stay readable and editable as
  native Python
- LLM-friendly means intermediate artifacts stay executable and reparsable after
  mutation

This is the meaning of “AST all the way”.

## Semantic owner

HTP should not treat JSON sidecars or raw Python AST as the semantic owner.

The semantic owner is a typed Python object graph rooted at `ProgramModule`.

Python source / AST remains essential, but as:

- authoring input
- persistence / rendering format
- normalized staged artifact format

## Normalized HTP Python

HTP uses one normalized Python dialect across all IR families.

That dialect should:

- use ordinary Python module syntax
- construct typed HTP objects explicitly
- be stable enough for exact semantic round-tripping

Example shape:

```python
kernel = Kernel(...)
routine = Routine(...)
module = ProgramModule(...)
```

HTP does not attempt to preserve arbitrary original user syntax.

## Round-trip law

The required contract is:

- `parse_python(source) -> ProgramModule`
- `emit_python(module) -> source`
- `parse_python(emit_python(module)) == equivalent ProgramModule`

Equivalence is semantic and executable equivalence, not source-text identity.

## Executable unit

A committed HTP stage artifact is a Python module that reconstructs a
`ProgramModule` and exposes `run(...)`.

Execution should run the reconstructed typed object graph. It must not rely on
raw-AST walking as the primary semantic model.

## ProgramModule

`ProgramModule` is the minimum semantic owner object.

Required fields:

- `items`
- `aspects`
- `analyses`
- `identity`
- `entrypoints`
- `meta`

Field roles:

- `items`
  - executable typed IR graph
- `aspects`
  - long-lived semantic attachments
- `analyses`
  - invalidatable derived facts
- `identity`
  - ids, provenance, rewrite maps
- `entrypoints`
  - runnable named surfaces
- `meta`
  - non-semantic control metadata

## Execution rule

Every committed global stage must have a defined execution path.

That path is:

1. normalized HTP Python reconstructs `ProgramModule`
2. `run(...)` selects an entrypoint
3. interpreters execute typed objects in `ProgramModule.items`
4. runtime primitives discharge low-level operations

Transient non-executable forms are allowed only inside a pass, not as committed
stages.
