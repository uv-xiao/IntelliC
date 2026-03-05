# HTP Full Story — Analysis, Rationale, and Concrete Design

This document is the “single narrative” for the redo: it ties together **WHY → WHAT → HOW**, with concrete interfaces and
explicit contracts. It is intended to be “ready to implement” guidance, not a loose set of ideas.

Read order:
- WHY: `docs/design/analysis.md`
- WHAT: `docs/design/features.md`
- HOW: `docs/design/implementations.md`
- E2E sketches: `docs/design/examples.md`

This story focuses on: the minimal stable core, the exact extension surfaces, and the artifact contract that makes the
system debuggable, retargetable, and agent-friendly.

---

## 0) The problem we are solving (in one paragraph)

Modern ML systems need to compile **kernels → megakernels → serving routines** to many hardware targets with incompatible
execution, memory, and synchronization models. Existing ecosystems tend to split into:

- *Graph-level compilers* (e.g., XLA) that are retargetable at tensor-algebra level but struggle to expose/extend low-level
  semantics; and
- *Kernel DSL compilers* (e.g., Triton/TileLang) that expose low-level control but accumulate per-arch/per-vendor pipelines
  and implicit invariants that are hard to extend safely.

HTP’s thesis: the only scalable path is **contract-first extensibility**: explicit capabilities, typed layout/effects, and
artifact contracts that make compositions checkable and retargeting diagnosable.

---

## 1) What the user writes (concrete programming surfaces)

HTP is Python-first. The primary user-facing surfaces are:

### 1.1 Kernels (tile-level)

```python
from htp import kernel
from htp.types import Tile, f16, In, Out
from htp.intrinsics import portable, pto

@kernel
def add_tile(a: In[Tile[16, 16, f16]], b: In[Tile[16, 16, f16]], c: Out[Tile[16, 16, f16]]):
    c[:] = portable.add(a, b)
```

Key design points:
- A kernel is a typed function. Types carry tile shape + dtype (and later layout facets).
- Intrinsics are called as typed primitives. Backends provide lowering/emitters for intrinsic sets.

### 1.2 WSP programs (workload + schedule)

```python
from htp import workload, schedule, P

@workload
def add(A, B, C):
    for i in P(0, M // 16):
        for j in P(0, N // 16):
            add_tile(A.tile(i, j), B.tile(i, j), C.tile(i, j))

@schedule(add)
def add_sched(s):
    s.tile("i", 4).tile("j", 4)
    s.buffer("A", space="UB").buffer("B", space="UB")
    s.pipeline(stages=2)
```

Key design points:
- Workload is semantic; schedule is constraints. Schedules must be checkable against backend capabilities.

### 1.3 CSP programs (process/channel pipelines)

```python
from htp import process, Channel, connect, consume

l2c = Channel("l2c", depth=2)
c2s = Channel("c2s", depth=2)

loader = process("loader").produces(l2c).body(...)
computer = process("computer").consumes(l2c).produces(c2s).body(...)
storer = process("storer").consumes(c2s).body(...)

pipeline = connect([loader, computer, storer], [l2c, c2s])
```

Key design points:
- Channels are typed, bounded, and effect-checked.
- Backends lower CSP differently (sim/runtime/AIE-FIFO), but the CSP graph form is canonical.

---

## 2) What the compiler does (a contracted, inspectable pipeline)

### 2.1 The internal “IR” is AST + typed metadata

HTP’s default IR is:
- Source AST → Canonical AST → Typed AST

Typed metadata includes:
- symbol table + types
- layout facets (distribution/memory/hardware)
- effects/protocol obligations (channels, collectives, async handoffs)
- schedule directives

See: `docs/design/impls/01_ir_model.md`.

### 2.2 Passes are the primary extension unit

A pass is registered with:
- name + version
- `requires/provides/invalidates` capabilities
- diagnostics schema
- tracing hooks

See: `docs/design/impls/02_pass_manager.md`.

### 2.3 Pipelines are selected by satisfiability, not by “if backend == …”

Given:
- program capabilities inferred from AST + enabled dialects + imported intrinsic sets
- target backend requirements

HTP selects a pipeline by solving the `requires/provides` graph.

See: `docs/design/impls/03_capability_solver.md`.

---

## 3) What a backend must provide (explicit surface area)

Backends are plugins. A backend provides:

1) **ArchModel**
- hierarchy (levels of parallelism / placement)
- memory spaces (with alignment/capacity constraints)
- async primitives (copy, DMA, bulk transfer kinds)
- barrier/event model

2) **Intrinsic handlers**
- lowering rules (typed AST → backend-ready form)
- emitter rules (backend-ready form → artifact files)

3) **Artifact contract**
- package layout (files, roles, entrypoints)
- manifest extension fields

See:
- `docs/design/feats/07_backends_artifacts.md`
- `docs/design/impls/05_backend_pto.md`
- `docs/design/impls/06_backend_aie.md`

---

## 4) What “artifact-first” means (the non-negotiable integration boundary)

Every compile emits a directory tree with:
- `manifest.json` (schema + versions + pipeline + target + capabilities)
- `ir/` dumps (AST snapshots, typed metadata snapshots)
- `pass_trace.jsonl` (before/after pointers, timings, diagnostics)
- `codegen/<backend>/...` outputs

See: `docs/design/impls/04_artifact_manifest.md`.

This is what makes:
- debugging practical,
- runtime integration stable,
- and agentic compiler development feasible (artifacts are “context packs”).

HTP can do something most compilers cannot: because the canonical form is Python AST, each stage can also emit a
**runnable Python replay program** (`ir/stages/<id>/program.py`). This makes intermediate artifacts executable, enabling
stage-by-stage debugging and simulation without bespoke IR runners.

---

## 5) Extensibility: the exact surfaces and how they compose

HTP extension units:
- dialect package
- intrinsic set
- pass
- pipeline template
- backend
- binding/runtime adapter

Composition rule:
- every unit must declare `requires/provides` capabilities, and all cross-cutting semantics must be represented as typed
  layout facets and effects.

See: `docs/design/feats/01_extensibility.md`.

---

## 6) Retargetability: how HTP avoids “attrs as APIs”

Retargetability fails when the “true contracts” are hidden in:
- pass ordering,
- target-specific branches,
- and target-only dialect ops.

HTP’s answer is:
- capability typing + solver-based pipelines,
- typed effects/protocol obligations,
- and explicit backend surfaces (ArchModel + handlers + artifact contract).

Evidence and comparison:
- `docs/design/reports/retargetable_extensibility_report.md`

---

## 7) Agentic compiler development (fully autonomous, healthy)

HTP should be designed so agents can safely evolve the compiler:
- bounded edit surfaces (“safe corridors” templates)
- non-negotiable verification gates
- structured provenance recorded in manifests (`extensions.agent.*`)

See:
- `docs/design/feats/10_agentic_development.md`
- `docs/design/impls/10_agentic_tooling.md`

---

## 8) Definition of done (design completeness)

The redo design is “complete enough to implement” when:

- Every extension surface above has a concrete interface and a contract.
- Every compiler stage has an artifact/tracing output.
- Every backend/binding contract is explicit and testable via golden artifact checks.
- Every “open question” is either resolved or explicitly recorded as deferred research/non-goal.
