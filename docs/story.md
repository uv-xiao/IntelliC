# HTP Story

HTP aims to be a Python-AST-centric compiler framework for heterogeneous tile programs, structured kernel programs, and workload/dataflow programs that span multiple hardware backends without fragmenting into backend-local compiler stacks.

## Final intended shape

The intended framework has six layers.

### 1. Compiler model

Python remains the semantic home. Every compilation stage should still correspond to runnable Python in `sim`, while semantic state, identity, layout, effects, schedules, and backend discharge facts are emitted as explicit artifacts.

### 2. Programming surfaces

Users should author kernels, schedules, channels, and serving routines as native Python programs. WSP and CSP are not special side compilers; they are frontend surfaces over the same shared substrate.

### 3. Pipeline and solver

Passes, pipelines, and optional extension islands should be selected through explicit contracts rather than folklore about pass order. Retargetability comes from shared semantics plus typed composition, not from cloning a new compiler stack for each backend.

### 4. Artifacts and debug

Compiler state must stay inspectable. Replay, staged sidecars, diagnostics, maps, traces, and codegen indices are not debugging accidents; they are part of the framework contract.

### 5. Backends and extensions

PTO, NV-GPU, AIE, and future targets should consume the same semantic model and discharge it through explicit backend contracts. MLIR and vendor toolchains are extension mechanisms or artifact boundaries, not the native semantic owner of HTP.

### 6. Agent-native development

HTP is also intended to be a healthy long-term environment for autonomous and semi-autonomous compiler development. That requires stable schemas, replayable intermediate artifacts, strong diagnostics, narrow edit corridors, controlled PR workflow, and examples/tests that are readable enough for humans and reliable enough for agents.

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

## Repository split

- `docs/design/` documents the implemented subset
- `docs/todo/` documents the remaining layers and gaps
- `docs/in_progress/` tracks feature-branch work currently being built
- `docs/reference/` and `docs/research/` remain supporting corpora
