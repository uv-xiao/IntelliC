# Feature: Binding & Runtime Interface

## Goal

Provide a consistent “compile → bind → run” workflow while allowing backend-specific build/run.

Bindings are backend plugins that connect artifact packages to actual execution (sim or device). They are also the natural
home for:

- validation of artifact contracts,
- replay (stage-by-stage `RunnablePy`) integration,
- runtime tracing/profiling hooks,
- and build toolchain invocation (when codegen emits sources/recipes rather than final binaries).

---

## Binding responsibilities

- validate package against backend contract
- optionally build artifacts (invoke toolchain) into executable form
- load artifacts (dlopen, runtime API, simulator)
- run entrypoints with typed argument marshalling
- provide tracing hooks
- support `replay(stage_id, mode=sim|device)` (stages always provide `program.py` runnable in `sim`)

Design constraint:

- stages always provide `program.py` and are runnable in `mode="sim"` (they may be stubbed with explicit diagnostics)

The runtime story has two separate layers:

- `htp.runtime`: replay/runtime support for stage programs and structured replay diagnostics
- backend bindings: real package execution integration against external runtimes/toolchains

HTP should keep these separate so the canonical Python-space pipeline remains debuggable even when external execution is
not available.

## Runtime separation

HTP should not embed device runtimes; it integrates with:

- PTO runtime/toolchain for Ascend
- NV-GPU build/runtime tooling
- MLIR-AIE build/run tooling for AIE extensions
- future backends via binding plugins

Concretely:

- PTO package execution should map onto the current `pto-runtime` builder/compiler/bindings stack.
- NV-GPU package execution should follow an adapter-based model similar to the source-first integration pattern used by
  TileLang.

Deep dive:
- binding interface: `docs/design/impls/07_binding_interface.md`
