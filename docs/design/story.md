# HTP Full Story — Contract-First, Artifact-First Compilation for Retargetable Kernels

This document is the single narrative that ties together **WHY → WHAT → HOW** in a form that is meant to be
“ready to implement”. It is written in a paper-like style because HTP is fundamentally a systems-design claim:
retargetable extensibility is not a bag of features; it is an architecture that prevents feature work from collapsing
into per-target pass soups.

Read order for details:

- WHY (problem + critique + evidence): `docs/design/analysis.md`
- WHAT (feature surfaces + contracts): `docs/design/features.md`
- HOW (architecture + components): `docs/design/implementations.md`
- E2E examples: `docs/design/examples.md`
- Deep evidence report (Triton/JAX/TileLang/MLIR): `docs/design/reports/retargetable_extensibility_report.md`

---

## Abstract

ML compiler stacks must increasingly target heterogeneous hardware while supporting rapid extension: new memory
primitives, new scheduling strategies, new synchronization protocols, and new “kernel micro-architectures” such as
warp specialization and software pipelining. Existing approaches often force a choice between portability and control.
Graph compilers are portable but opaque at low-level semantics; kernel DSL compilers are expressive but accumulate
target-specific lowering pipelines whose implicit invariants resist extension.

HTP’s thesis is that retargetable extensibility requires a different core: **contract-first compilation** with explicit
capability typing, typed layout/effects, and artifact-first staging. HTP is **AST-first**: the canonical IR is a typed
Python AST, and every intermediate stage is intended to be recoverable as a **runnable Python replay program**. Passes
are explicit about two effect kinds—AST mutation and analysis production—and both are staged as artifacts. Pipelines are
selected by satisfiability rather than backend-specific branching. Together these choices make extension work checkable,
debuggable, and long-term maintainable.

---

## 1. Motivation: what goes wrong in “IR + passes” retargeting

Retargeting fails in practice not because a compiler lacks an IR, but because the *real contracts* live elsewhere:

- in undocumented pass ordering requirements,
- in target-specific “attrs as APIs” conventions that leak across passes,
- and in analyses that exist as ephemeral caches rather than staged evidence.

When a feature spans multiple layers (front-end surface, analysis, transformation, backend discharge), the absence of
explicit contracts causes the work to become target-owned. Warp specialization and software pipelining are canonical
examples: their correctness hinges on precise async and barrier semantics, and their performance hinges on target
capabilities and resource constraints.

HTP treats this as a design constraint: if the system cannot *explain* why a transformation is legal and what it assumed,
it is not retargetable in the long run.

---

## 2. Design goals (what HTP optimizes for)

HTP makes a small number of goals primary:

1) **Retargetable extensibility**: adding a feature should primarily mean adding a small number of capability-gated passes
   and intrinsic handlers, not rewriting backends.
2) **Inspectable compilation**: every pass produces a staged snapshot with traceable diagnostics and evidence.
3) **Executable intermediates**: because the canonical IR is Python AST, each stage can emit runnable `program.py` for
   replay and debugging (with explicit stub contracts when needed).
4) **Composable contracts**: layout, effects, and capabilities are typed and staged; pipelines are satisfiable or rejected
   early with explainable reasons.

These goals bias the architecture toward explicitness and away from implicit conventions.

---

## 3. Programming model: intent, constraints, and protocols

HTP is Python-first. Users write programs in three mutually reinforcing surfaces:

### 3.1 Kernels (tile-level intent)

Kernels are typed functions over tiles/tensors and call typed intrinsics. The kernel expresses semantic intent (e.g.,
async copy, barrier scope) without committing to a target-specific primitive.

### 3.2 WSP (workload + schedule)

WSP separates:

- the semantic workload (what computation happens), and
- the schedule (constraints on mapping/buffering/pipelining).

Schedules are not “imperative rewrite scripts”; they are constraints that must be checked against target capabilities.

### 3.3 CSP (process/channel pipelines)

CSP makes pipeline parallelism explicit via typed channels and effect-checked protocols. Backends may implement channels
in very different ways, but the CSP graph is the canonical contract surface.

---

## 4. Compiler architecture: AST-first, artifact-first, contract-first

### 4.1 IR: typed Python AST + staged analyses

HTP’s canonical IR is a typed Python AST plus attached metadata snapshots (types/layout/effects/schedule). A crucial
addition is that analyses are first-class and staged: if an analysis justifies a rewrite, it is emitted under
`ir/stages/<id>/analysis/` and indexed.

HTP also treats replay as an invariant, not a best-effort feature:

- every stage program is runnable in `mode="sim"` (possibly stubbed with explicit diagnostics), which constrains what IR
  extensions are allowed and forces external toolchains to remain explicit accelerators rather than semantic owners.

Deep dive: `docs/design/impls/01_ir_model.md`

### 4.2 Passes: two effect kinds, explicitly recorded

During compilation, passes may have two observable effect kinds:

- **AST mutation**: produces a new typed AST and typically a new runnable replay stage program.
- **Analysis production**: produces typed, versioned data structures used by later passes and humans/agents.

These are not internal implementation details; they are part of the pass contract and are recorded in the staged
artifacts and `ir/pass_trace.jsonl`.

Deep dive: `docs/design/impls/02_pass_manager.md`

### 4.3 Pipelines: satisfiable by construction

HTP selects pipelines by satisfiability. Given the program’s capabilities and the target’s declared capabilities, the
solver checks that every pass contract is satisfiable before execution. Failure is explained as a missing capability,
handler, invariant, or artifact output—not as a late “backend crash”.

Deep dive: `docs/design/impls/03_capability_solver.md`

### 4.4 Artifacts: the integration boundary, not an afterthought

Every compile emits a package that is both:

- a runtime integration boundary (bindings consume it), and
- a debugging/research substrate (humans/agents inspect and replay it).

The package includes:

- a manifest (`manifest.json`) with versions, capabilities, target, and stage graph,
- per-stage dumps (`program.pyast.json`, typed metadata, analysis outputs),
- `ir/pass_trace.jsonl` with structured pass events,
- backend outputs under `codegen/<backend>/...`.

Deep dive: `docs/design/impls/04_artifact_manifest.md`

### 4.5 Backends and islands: explicit, auditable boundaries

Backends are plugins. Each backend must provide:

- an `ArchModel` (hierarchy, memory spaces, async/barrier semantics),
- intrinsic handlers (lower/emit/simulate),
- and an artifact contract.

External toolchains (MLIR-AIE, vendor compilers, etc.) are treated as **explicit compilation islands** that are entered
and exited by contracted passes; they do not become hidden global dependencies.

Deep dives:

- PTO backend packaging: `docs/design/impls/05_backend_pto.md`
- AIE island contract: `docs/design/impls/06_backend_aie.md`

---

## 5. Case study: warp specialization + software pipelining, as contracts

Warp specialization and software pipelining are a stress test: they mix planning and rewriting, they require explicit
async and barrier semantics, and they must adapt to target capabilities.

HTP’s design makes the structure explicit:

- analyses produce a role plan and a pipeline plan (staged, versioned artifacts),
- transform passes apply the plan by rewriting the typed AST,
- discharge passes map portable protocols into target primitives behind capability gates,
- and every stage can remain runnable in Python when contracts allow, enabling replay-based debugging.

Complete end-to-end walkthrough:

- `docs/design/impls/11_case_study_warp_specialization_pipelining.md`

This is the smallest example that exercises HTP’s core claims: explicit pass effects, staged analyses, and explicit
retargeting boundaries.

---

## 6. Why HTP aims to do better than MLIR-first construction

MLIR’s IR + pass ecosystem is powerful, but it does not by itself guarantee retargetable extensibility. In practice,
retargeting failures come from:

- contracts encoded as conventions (pass order, attribute interpretation, dialect coupling),
- analyses that are not staged and therefore become invisible assumptions,
- and backend-owned expansions that are hard to reason about across targets.

HTP’s approach is not “anti-MLIR”; it is “MLIR as an explicit island”. HTP uses the Python AST as the canonical form and
requires that any external IR boundary be explicit, replayable (via stubs when needed), and auditable via artifacts.

For detailed comparative evidence (including Triton’s roadmap features and concrete pass complexity), see:

- `docs/design/reports/retargetable_extensibility_report.md`

---

## 7. Long-term development: why this architecture stays healthy

A compiler remains healthy when it accumulates explicit invariants rather than implicit ones. HTP bakes this into:

- pass contracts (`requires/provides/invalidates` + invariants),
- staged analyses (no “critical data lives only in RAM caches”),
- and a stable artifact substrate for golden tests and autonomous repair loops.

Agentic development is therefore a direct consequence of the design, not a bolt-on feature:

- `docs/design/impls/10_agentic_tooling.md`

---

## 8. Definition of done (design completeness)

The redo design is “complete enough to implement” when:

- every extension surface has a concrete interface and a contract,
- every pipeline stage has an artifact/tracing output (including analyses where relevant),
- every backend/binding contract is explicit and testable via golden artifact checks,
- and open questions are either resolved or explicitly recorded as deferred.

Operational checklist:

- `docs/design/acceptance_checklist.md`
