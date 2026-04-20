# Alignment and Product Gaps

This document tracks the concrete gaps reopened by the current repository
review. These are not vague ambitions. They are places where the codebase is
either narrower than the framework story, or where the docs currently imply
more closure than the product deserves.

## Why this topic is open again

The repository completed its previous broad checklist, but the review showed
that “checklist complete” and “product complete” are not the same thing.

The reopened work falls into four broad buckets:

- programming-surface quality,
- flagship example realism,
- backend depth,
- and documentation / status discipline.

## Scope checklist

### AST-all-the-way redesign

- [x] define the end-to-end invariant that every global stage artifact must be
      unparseable into native Python code for reading and human manipulation
- [x] define the companion invariant that every mutated stage artifact must also
      be runnable through a Python executor/interpreter path
- [x] redesign extension-island and MLIR participation around “return to
      Python-owned artifact at every global boundary”, not only “emit sidecars”
- [x] audit the current compiler model, pass contracts, artifact model, and
      backend discharge story against that stricter invariant
- [x] reopen any design document that currently treats the compiler model topic
      as fully closed even though the end-to-end AST-all-the-way target is not
      yet satisfied
- [x] make “human-friendly and LLM-friendly compiler stack” the primary design
      metric across examples, passes, and extension integration

### Programming surfaces

- [x] replace WSP stage-step metadata strings with more authored task-local body
      surfaces where possible
- [x] replace CSP `compute_step(...)` metadata with a more native process-body
      surface
- [x] reduce remaining builder ceremony in flagship WSP/CSP examples without
      reintroducing raw payload assembly
- [ ] ensure frontend and staged intermediate programs still read like native
      Python after non-trivial schedule and protocol rewrites

### Examples

- [x] raise flagship WSP examples to a clearer reference-grade mainloop story
- [x] raise flagship CSP examples to real protocol-rich process bodies instead
      of pipeline metadata choreography
- [x] keep example-local READMEs synchronized with the actual semantic proof
      surface

### Backend depth

- [ ] broaden NV-GPU device execution beyond the current positional-only,
      single-kernel-focused path
- [ ] broaden PTO runtime argument coverage beyond the current positional
      buffer/scalar execution model
- [ ] tighten AIE docs and implementation claims around what is reference
      toolchain support versus deeper backend support

### Pipeline and solver

- [x] ensure pass and extension contracts state whether they preserve
      Python-unparseable staged artifacts and runnable replay semantics at the
      next global boundary

### Documentation alignment

- [ ] keep `README.md`, `docs/design/`, and `docs/todo/` synchronized whenever
      review reopens a real gap
- [ ] keep design docs from declaring a topic “closed” when the current product
      still has a user-visible quality gap

## Current evidence

Programming-surface and example gaps are visible in:

- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `htp/ir/frontends/ast_lowering.py`
- `htp/ir/program/compose.py`
- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `examples/csp_channel_pipeline/demo.py`
- `examples/ast_frontend_composability/demo.py`
- `docs/design/programming_surfaces.md`
- `docs/design/littlekernel_ast_comparison.md`
- `docs/story.md`

Backend-depth gaps are visible in:

- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp/bindings/pto_runtime_adapter.py`
- `htp/bindings/aie_toolchain_adapter.py`
- `docs/design/backends_and_extensions.md`

Documentation-alignment gaps are visible in:

- `README.md`
- `docs/design/status_and_alignment.md`
- `docs/todo/README.md`

## Completion rule

This topic is not closed by passing tests alone.

It is closed only when:

- the global compiler story really enforces AST all the way instead of only
  using replayable Python at selected points,
- the public surfaces and examples are materially more native and less
  metadata-heavy,
- the backend contracts are documented at the same level of depth they actually
  implement,
- and the top-level repo docs no longer need caveats about overclaiming current
  completeness.
