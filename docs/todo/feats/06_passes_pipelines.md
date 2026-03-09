# Feature: Passes and Pipelines

## Goal

Make transformation pipelines:

- explicit
- inspectable
- extensible
- safe to compose
- replayable as staged runnable artifacts

## Pass types

- Canonicalization passes (AST normalization)
- Typing passes (layout/effect checks and normalization)
- Scheduling passes (apply schedule directives)
- Lowering passes (to backend-ready forms)
- Packaging passes (artifact emission, manifest finalization)
- Extension passes (e.g. MLIR round-trip islands or external-toolchain-specific transforms)
- Analysis passes (produce staged, versioned analyses for downstream transforms)

## Contract-driven execution

Each pass declares:

- `requires` capabilities
- `provides` capabilities
- `invalidates` capabilities (optional)
- layout/effect invariants and failure diagnostics
- replay contract (`RunnablePy`: preserves | stubbed; stages are always runnable in `sim`)
- if stubbed, the stage remains executable but may raise structured diagnostics when a stubbed region is reached
- pass effect kind (`analysis | transform | mixed`) and AST effect (`preserves | mutates`)

Deep dive:
- pass manager and tracing: `docs/design/impls/02_pass_manager.md`
- satisfiable pipeline selection: `docs/design/impls/03_capability_solver.md`

## Pipeline definition

A pipeline declares:

- target backend
- ordered pass list + parameters
- output artifact contract + binding requirement

Pipeline selection checks satisfiability before running.
