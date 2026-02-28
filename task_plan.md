# Task Plan: Retargetable Extensibility for ML Compilers (HTP vs Triton/JAX/TileLang/MLIR)

## Goal
Produce a research-grade report that explains:

1) What *actually* makes an ML compiler **retargetable** and **extensible** across heterogeneous hardware (GPU/NPU/AIE/etc.),
2) Why this is hard in practice in existing systems (Triton, JAX/XLA, TileLang/TVM, MLIR-based stacks), using concrete code-level examples,
3) What should make **HTP** special and why its design choices can win.

Deliverables are Markdown docs committed under `docs/future-htp/` (plus supporting planning files at repo root).

## Current Phase
Phase 3

## Phases

### Phase 1: Requirements & Discovery
- [x] Restate the questions precisely (retargetability/extensibility; why MLIR pass+IR can fail; what HTP should do differently)
- [ ] Gather primary sources (Triton roadmap blog, Triton codebase pointers, zhihu/little-kernel opinion in `references/size-littlekernel.md`)
- [ ] Identify 2–3 concrete optimizations as case studies (e.g., warp specialization, async TMA+barriers, shared-memory swizzle)
- [ ] Document findings in `findings.md`
- **Status:** complete

### Phase 2: Evaluation Framework
- [x] Define a “retargetability checklist” (semantic contracts, memory model, scheduling model, layout/effects, cost model, debug/IR visibility, backend surface area)
- [x] Define what “extensibility” means operationally (what can 3rd parties add without forking core?)
- [x] Decide report structure and file layout
- **Status:** complete

### Phase 3: Triton Case Study (roadmap + code)
- [x] Read Triton roadmap blog (warp specialization) and extract claims/features
- [x] Clone `triton-lang/triton` into `references/triton/`
- [ ] Map the relevant compiler IR layers and pass pipelines in Triton
- [ ] For each chosen optimization, locate the implementing passes/files and explain cross-target complexity
- [ ] Summarize why general retargetability is constrained by Triton’s design choices
- **Status:** in_progress

### Phase 4: JAX/XLA/StableHLO and TileLang/TVM Case Studies
- [ ] Summarize where retargetability is strong (HLO portability) and where extensibility is weak (hard to add new low-level semantics)
- [ ] TileLang/TVM: discuss schedule primitives, target integration, memory/layout model, and extension burden
- [ ] Tie back to checklist
- **Status:** pending

### Phase 5: MLIR Construction Analysis
- [ ] Explain what MLIR *does* provide (dialects, interfaces, patterns, passes)
- [ ] Analyze failure modes for heterogeneous retargeting (implicit invariants, pass ordering brittleness, dialect boundary friction, backend-specific lowering leakage)
- [ ] Identify what must be added beyond “IR+passes” to scale (capability typing, effect systems, explicit hardware contracts, artifact contracts)
- **Status:** pending

### Phase 6: HTP Synthesis (Why HTP can win)
- [ ] Define HTP differentiators as enforceable mechanisms (capabilities/effects/layout facets/artifacts, not slogans)
- [ ] Show how HTP would represent + type-check the same optimizations in a backend-agnostic way
- [ ] Propose an HTP extension model that is demonstrably easier than patching Triton/MLIR stacks
- **Status:** pending

### Phase 7: Write Report + Review
- [ ] Write the report file(s) under `docs/future-htp/`
- [ ] Cross-check claims against source code locations
- [ ] Ensure per-point detailed examples and tradeoffs
- **Status:** pending

## Key Questions
1. What are the *minimum semantic contracts* required to retarget reliably (memory spaces, async, barriers, vector semantics, layout/effects)?
2. Where do “IR+passes” break down without stronger contracts?
3. What is the smallest set of extra mechanisms that make extensibility real (capabilities, effects, artifact contracts, etc.)?
4. For a concrete optimization (warp specialization), what code surfaces change in Triton, and what does that imply for adding a new backend?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use 2–3 optimization case studies | Forces concrete, code-grounded analysis |
| Focus on contracts beyond passes | Addresses “why MLIR pass+IR can fail” directly |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Tool exec failures due to missing cwd `/home/uvxiao/pto-wsp` | 1 | Use correct repo path `/home/uvxiao/htp` via explicit workdir |

## Notes
- After every 2 source/code browsing actions, update `findings.md`.
