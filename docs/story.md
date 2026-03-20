# HTP Story

HTP aims to be a Python-AST-centric compiler framework for heterogeneous tile
programs, structured kernel programs, and workload/dataflow programs that span
multiple hardware backends without fragmenting into backend-local compiler
stacks.

Its primary product goal is stronger than “retargetable compiler”. HTP is meant
to be both:

- human-friendly, so intermediate compiler state remains readable and editable
  as native Python;
- LLM-friendly, so intermediate compiler state remains runnable and
  mechanically rewritable through a Python executor/interpreter path.

The discipline that is supposed to make that possible is AST all the way.

## Final intended shape

The intended framework has six layers.

### 1. Compiler model

Python remains the semantic home. Every compilation stage should still
correspond to runnable Python in `sim`, while semantic state, identity, layout,
effects, schedules, and backend discharge facts are emitted as explicit
artifacts.

That requirement is stronger than “the compiler internally stores Python AST”.
At every global stage boundary, the current compiler-owned form should still be
unparseable back into native Python code. Even after extension islands or MLIR
pipelines, the compiler must return to a Python-owned stage artifact before the
next global boundary.

### 2. Programming surfaces

Users should author kernels, schedules, channels, and serving routines as native Python programs. WSP and CSP are not special side compilers; they are frontend surfaces over the same shared substrate.

### 3. Pipeline and solver

Passes, pipelines, and optional extension islands should be selected through explicit contracts rather than folklore about pass order. Retargetability comes from shared semantics plus typed composition, not from cloning a new compiler stack for each backend.

### 4. Artifacts and debug

Compiler state must stay inspectable. Replay, staged sidecars, diagnostics, maps, traces, and codegen indices are not debugging accidents; they are part of the framework contract.

The key artifact rule is that intermediate artifacts are not only machine data.
They are supposed to be readable, native-looking Python snapshots that a human
or agent can inspect, edit, and rerun.

### 5. Backends and extensions

PTO, NV-GPU, AIE, and future targets should consume the same semantic model and discharge it through explicit backend contracts. MLIR and vendor toolchains are extension mechanisms or artifact boundaries, not the native semantic owner of HTP.

### 6. Agent-native development

HTP is also intended to be a healthy long-term environment for autonomous and semi-autonomous compiler development. That requires stable schemas, replayable intermediate artifacts, strong diagnostics, narrow edit corridors, controlled PR workflow, and examples/tests that are readable enough for humans and reliable enough for agents.

This is the deepest reason for AST all the way. If a pass, backend discharge
step, or extension island leaves the framework in a form that cannot be
unparsed to runnable Python, then HTP has failed its own long-term product
goal.

## Visual overview

```text
Python authoring
    |
    v
shared compiler model
    |
    v
passes + solver + extension islands
    |
    v
artifacts + replay + diagnostics
    |
    v
backends / runtimes / toolchains
    |
    v
human + agent development loop
```

## Current implication

This final story is stricter than the current implementation. The repository
already proves the core direction, but the stronger “human + LLM friendly via
AST all the way” rule now reopens product work under `docs/todo/`.

## Repository split

- `docs/design/` documents the implemented subset
- `docs/todo/` documents the remaining layers and gaps
- `docs/in_progress/` tracks feature-branch work currently being built
- `docs/reference/` and `docs/research/` remain supporting corpora
