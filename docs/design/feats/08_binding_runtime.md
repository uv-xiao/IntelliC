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

## Runtime separation

HTP should not embed device runtimes; it integrates with:

- PTO runtime/toolchain for Ascend
- MLIR-AIE build/run tooling for AIE
- future backends via binding plugins

Deep dive:
- binding interface: `docs/design/impls/07_binding_interface.md`
