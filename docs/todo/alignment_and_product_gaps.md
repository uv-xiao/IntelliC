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

### Programming surfaces

- [ ] replace WSP stage-step metadata strings with more authored task-local body
      surfaces where possible
- [ ] replace CSP `compute_step(...)` metadata with a more native process-body
      surface
- [ ] reduce remaining builder ceremony in flagship WSP/CSP examples without
      reintroducing raw payload assembly

### Examples

- [ ] raise flagship WSP examples to a clearer reference-grade mainloop story
- [ ] raise flagship CSP examples to real protocol-rich process bodies instead
      of pipeline metadata choreography
- [ ] keep example-local READMEs synchronized with the actual semantic proof
      surface

### Backend depth

- [ ] broaden NV-GPU device execution beyond the current positional-only,
      single-kernel-focused path
- [ ] broaden PTO runtime argument coverage beyond the current positional
      buffer/scalar execution model
- [ ] tighten AIE docs and implementation claims around what is reference
      toolchain support versus deeper backend support

### Documentation alignment

- [ ] keep `README.md`, `docs/design/`, and `docs/todo/` synchronized whenever
      review reopens a real gap
- [ ] keep design docs from declaring a topic “closed” when the current product
      still has a user-visible quality gap

## Current evidence

Programming-surface and example gaps are visible in:

- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `examples/csp_channel_pipeline/demo.py`
- `docs/design/programming_surfaces.md`
- `docs/design/littlekernel_ast_comparison.md`

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

- the public surfaces and examples are materially more native and less
  metadata-heavy,
- the backend contracts are documented at the same level of depth they actually
  implement,
- and the top-level repo docs no longer need caveats about overclaiming current
  completeness.
