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

## Landed priorities

The following priorities are now implemented:

- capability solver
- agent-facing tooling
- semantic breadth expansion baseline
- MLIR round-trip expansion baseline
- optional AIE extension backend

## Remaining broader priorities

### Priority 1 — Solver evolution

- richer extension/package composition rules
- backend-owned capability declarations instead of the current local tables
- broader alternative-choice support

### Priority 2 — Agent-loop productization

- autonomous patch / verify / promote loop
- policy files and bounded edit corridors
- minimization and richer decision-trace provenance

### Priority 3 — Semantic breadth expansion

Required deliverables:

- more kernel ops
- more workload/dataflow/channel/process semantics
- stronger legality and effect checking than the current baseline

### Priority 4 — MLIR round-trip expansion

Required deliverables:

- richer exporter/importer tables
- more than the current scalar elementwise subset
- deeper round-trip validation

### Priority 5 — Optional extension backends

Required deliverables:

- AIE device/toolchain execution
- additional extension backends beyond AIE

## Acceptance rule for this phase

This broader design/research phase is succeeding when:

- every future major feature is placed into a priority order with explicit
  dependency reasoning
- future docs are aligned with the current proved baseline
- the next implementation targets are stated as concrete, testable deliverables
  rather than open-ended aspirations
