# HTP Story

HTP aims to be a Python-AST-centric compiler framework for heterogeneous tile programs, kernel programs, and structured workload/dataflow programs.

The final intended framework has four defining properties.

## 1. Python remains the semantic home

Programs are authored as native Python programs, not as opaque data blobs. Compilation may attach staged semantic payloads, analyses, backend artifacts, and extension-owned side paths, but the canonical form remains runnable Python-space IR. Every stage should remain runnable in `sim` or fail through a structured replay diagnostic.

## 2. Compiler state is explicit and inspectable

HTP should never hide the real state of compilation inside transient pass-local caches alone. Identity maps, semantic payloads, layout/effect facts, schedule state, pass traces, solver decisions, backend codegen indices, and runtime/build traces are all intended to be explicit artifacts. This is a design choice for retargetability, debuggability, and agent-friendliness.

## 3. Retargetability comes from contracts, not pass soup

HTP is intended to support multiple hardware targets and extension pathways without letting each backend own a separate compiler architecture. Core semantics, layout/effect typing, and schedule intent should stay shared. Backends and extensions should consume explicit contracts and discharge them into target mechanisms.

## 4. Agent development is a first-class target

The framework is intended to support long-lived agent-driven compiler development. That requires:
- replayable intermediate programs,
- stable emitted schemas,
- explicit diagnostics and fix-hint surfaces,
- narrow edit corridors,
- and a disciplined repo workflow that exposes TODO, in-progress, and implemented states separately.

## Intended feature envelope

The full intended framework spans:
- kernel semantics and workload/dataflow semantics,
- WSP and CSP authoring surfaces,
- solver-driven pass/pipeline composition,
- explicit intrinsics and discharge contracts,
- MLIR round-trip extensions,
- multiple backend/runtime integrations,
- and a full agent-product loop for replay, diff, minimization, bisect, verification, and controlled promotion.

## Docs split

- `docs/design/` documents the implemented subset.
- `docs/todo/` documents the remaining feature set and research-backed direction.
- `docs/in_progress/` tracks feature branches currently being built.

## Source material for this story

This top-level story is the repository-level synthesis of:
- `docs/todo/analysis.md`
- `docs/todo/features.md`
- `docs/todo/story.md`
- `docs/todo/reports/retargetable_extensibility_report.md`
