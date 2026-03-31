# Current Status and Alignment

This document is the implementation-backed status review of HTP. It answers a
different question from `docs/story.md`: not only what HTP aims to be, but what
the current repository actually proves, where the implementation is already
strong, and where the docs or product story still need to stay disciplined.

## Why this document exists

HTP uses its documentation tree as part of the product contract. That means the
repo needs an explicit place for a status review that separates:

- implemented and well-aligned behavior,
- implemented but still narrow behavior,
- and places where the narrative is currently stronger than the product.

Without that separation, `docs/design/` becomes too optimistic and
`docs/todo/` stays closed even when real product gaps remain.

## Visual model

```text
framework story
      |
      v
implemented contracts
      |
      +--> solid and aligned
      +--> implemented but narrow
      `--> overclaimed / reopened TODO
```

## Summary judgment

The repository is real and coherent.

The strongest parts today are:

- the Python-canonical compiler model,
- staged `ProgramModule` state bundles and replayable packages,
- pass / solver / artifact discipline,
- and the shared backend / extension contract structure.

The weakest parts today are:

- the framework does not yet fully satisfy the stricter “AST all the way for
  both human and LLM friendliness” target,
- the final frontend quality of WSP and especially CSP authoring,
- the breadth of backend execution beyond the flagship paths,
- and stale documentation that still implies broader closure than the current
  product actually deserves.

## Implemented and solid

### Compiler model

The compiler model is the most aligned part of the repository.

What is solid today:

- Python-space remains the canonical stage form.
- compilation stages emit compact `ProgramModule` state bundles with explicit
  kernel, workload, type, layout, effect, and schedule state.
- identity and mapping are first-class artifacts instead of implicit Python
  object identity.
- replay and semantic diff consume those staged artifacts directly.

Main code anchors:

- `htp/compiler.py`
- `htp/ir/semantics.py`
- `htp/ir/types.py`
- `htp/ir/layout.py`
- `htp/passes/program_model.py`
- `htp/passes/typecheck_layout_effects.py`

What is still not fully proved is the stronger end-to-end rule that every
global stage boundary is also served by equally strong frontend ergonomics. The
committed-stage contract is now Python-owned and interpreter-backed, but WSP
and CSP surface quality still keep the broader product goal open.

### Pipeline and solver

The repo does not yet claim a global super-optimizer, and that restraint is
important. What it does claim is already implemented:

- backend-owned solver declarations,
- pass and pipeline registries,
- solver preflight and failure reporting,
- explicit pass contracts,
- pass traces with state deltas and requirement satisfaction,
- extension-aware pipeline participation,
- and existing-package resume.

Main code anchors:

- `htp/solver.py`
- `htp/pipeline/defaults.py`
- `htp/pipeline/registry.py`
- `htp/passes/contracts.py`
- `htp/passes/manager.py`
- `htp/passes/trace.py`

### Artifacts, replay, and diagnostics

This is the clearest proof surface in the repository.

What is solid today:

- package layout is normative,
- manifest and staged records are validated,
- replay is a distinct execution surface over staged Python,
- stage `program.py` files are readable runnable Python modules,
- diagnostics and binding results are structured,
- and the tool layer (`replay`, `verify`, `diff`, `explain`, `bisect`,
  `minimize`, `policy-check`, `workflow-state`) is real code rather than design
  prose.

Main code anchors:

- `htp/artifacts/manifest.py`
- `htp/artifacts/stages.py`
- `htp/runtime/`
- `htp/tools.py`
- `htp/diagnostics.py`
- `htp/passes/replay_program.py`

## Implemented but narrow

### Programming surfaces

The kernel surface is in good shape. The routine surface is usable. The WSP and
CSP surfaces are better than raw payload assembly, but they are not yet the
final “native Python first” answer.

One real improvement is now in place: the current public frontend set
(`kernel`, `routine`, `wsp`, and `csp`) lowers through `ProgramModule`
entrypoints instead of dict-only compiler ingestion.

Current narrow points:

- WSP still expresses stage plans through builder calls and symbolic step names.
- CSP still relies on `compute_step("...")` metadata instead of authored
  process-local program bodies.
- flagship examples are now meaningful, but they still read more like
  structured schedule assembly than the best reference-calibrated Python DSL
  bodies.

Main code anchors:

- `htp/kernel.py`
- `htp/routine.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `examples/wsp_warp_gemm/demo.py`
- `examples/wsp_littlekernel_pipelined_gemm/demo.py`
- `examples/csp_channel_pipeline/demo.py`

### Backend depth

Backend substrate exists and the architecture is aligned, but the execution
depth is uneven.

Current narrow points:

- NV-GPU device execution is still a v1 path with positional-only arguments and
  a single-kernel runtime focus.
- PTO execution is real through `pto-runtime`, but it still accepts a narrower
  argument model than the full long-term framework story suggests.
- AIE is correctly extension-owned, but today it is still closer to a reference
  toolchain path than a deeply optimized production backend.

Main code anchors:

- `htp/bindings/nvgpu.py`
- `htp/bindings/nvgpu_cuda_adapter.py`
- `htp/bindings/pto.py`
- `htp/bindings/pto_runtime_adapter.py`
- `htp/bindings/aie.py`
- `htp/bindings/aie_toolchain_adapter.py`
- `htp_ext/aie/emit.py`

## Documented too strongly

The current repo has three concrete documentation problems.

### README completion state is stale

`README.md` previously implied that a reopened programming-surface TODO file was
still present, while `docs/todo/README.md` simultaneously claimed that no TODO
files remained. That kind of drift makes it hard to trust the docs boundary.

### LittleKernel comparison doc still pointed to a removed TODO file

`docs/design/littlekernel_ast_comparison.md` extracted valid surface lessons,
but it still pointed to a TODO file that no longer existed. The comparison is
useful; the old closure claim was not.

### “100% complete” was too strong

`docs/todo/README.md` had become a historical closure statement rather than a
current product assessment. The review shows that the repo had indeed completed
its old checklist, but had not actually closed the current frontend-quality and
backend-breadth questions.

## Reopened TODO boundary

The design review reopens concrete future work under `docs/todo/`.

The current broad reopened topic is:

- `docs/todo/alignment_and_product_gaps.md`

That file is now the correct place to track:

- programming-surface quality gaps,
- example realism gaps,
- backend-depth gaps,
- and doc/story overclaim cleanup that is not yet fully implemented.

## How to use this document

Use this file when you need to answer any of these questions:

- “What is actually solid in HTP today?”
- “Which parts are real but still narrow?”
- “Where do docs currently overstate the framework?”
- “Which gaps should be reopened as TODO instead of being argued about from
  memory?”

For feature design, combine this document with:

- `docs/story.md`
- `docs/design/README.md`
- `docs/todo/README.md`
- `docs/todo/alignment_and_product_gaps.md`
