# HTP Broader Design / Research Roadmap

**Date:** 2026-03-08

## Purpose

Define the next phase after substrate completion. The core architecture is now
proved in code; the remaining work is broader design/research scope that must
be turned into implementable, prioritized slices.

## Current proved baseline

Backed by current code and verification:

- replayable staged Python programs
- staged semantic/type/layout/effect/schedule payloads
- explicit pass contracts and pass tracing
- one extension-owned MLIR CSE path
- real PTO `a2a3sim` vector-add execution
- real NV-GPU GEMM execution on device

## Next-phase priorities

### Priority 1 — Capability solver

Why first:

- the substrate is explicit, but composition is still manually wired
- future growth now risks pipeline drift more than missing semantics

Required deliverables:

- `CapabilityState` model
- solver-visible pipeline templates
- `ir/solver_failure.json`
- tests for missing capability / stale analysis / missing final artifact

### Priority 2 — Agent-facing tooling

Why second:

- the agent-native substrate already exists in raw form
- it should become a real product surface before feature growth widens the
  system further

Required deliverables:

- `htp replay`
- `htp verify`
- `htp diff --semantic`
- `htp explain`
- structured `extensions.agent.*` provenance

### Priority 3 — Semantic breadth expansion

Why third:

- the current typed substrate is real but selective
- broader semantics should land on top of solver-visible, agent-visible
  contracts

Required deliverables:

- richer kernel op set
- richer workload/dataflow/channel/process semantics
- stronger legality and effect checking

### Priority 4 — MLIR round-trip expansion

Why fourth:

- the extension boundary is already proved
- broader MLIR use should come after the solver and agent tooling so extension
  composition remains controlled

Required deliverables:

- explicit eligible-subset matcher
- richer exporter/importer tables
- round-trip validation tests

### Priority 5 — Optional extension backends

Why fifth:

- additional backends should consume the matured composition layer rather than
  forcing it prematurely

Required deliverables:

- AIE / MLIR-AIE artifact contract
- binding/toolchain contract
- example and validation path

## Acceptance rule for this phase

This broader design/research phase is succeeding when:

- every future major feature is placed into a priority order with explicit
  dependency reasoning
- future docs are aligned with the current proved baseline
- the next implementation targets are stated as concrete, testable deliverables
  rather than open-ended aspirations
