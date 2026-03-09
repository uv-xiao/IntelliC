# Impl: Binding Interface (compile → bind → run → replay)

## Goal

Standardize `bind(package)` so users get a consistent experience across backends, while preserving backend-specific
build/run realities.

Bindings are also the execution substrate for:

- staged replay (`RunnablePy`) in `sim|device` modes,
- artifact contract validation,
- and trace/log collection.

The most important distinction is that bindings unify three different activities under one API surface:

- **stage replay**,
- **backend package execution**,
- **build/materialization**.

Current implementation anchors:

- binding selection: `htp/bindings/api.py`
- base binding lifecycle: `htp/bindings/base.py`
- PTO binding path: `htp/bindings/pto.py`
- NV-GPU binding path: `htp/bindings/nvgpu.py`

---

## 1) Binding lifecycle

1) **Validate**: validate package + manifest against backend artifact contract.
2) **Build** (optional): invoke toolchains to produce runnable binaries from `codegen/<backend>/...` sources/recipes.
3) **Load**: load runtime handles (shared libraries, device runners, simulators).
4) **Run**: execute entrypoints with typed marshalling and trace hooks.
5) **Replay**: execute a specific stage’s `ir/stages/<id>/program.py` (always runnable in `mode="sim"`; may be stubbed).
6) **Report**: emit structured run records, diagnostics, and log pointers into the package.

### 1.1 Stage replay vs package execution

These must not be conflated:

- **Replay**
  - imports and executes HTP-emitted `ir/stages/<id>/program.py`
  - is always Python-space
  - exists for verification, debugging, and localization
  - remains available even if no external runtime/toolchain is installed

- **Package execution**
  - executes the backend package as a backend package
  - may involve external compilers, shared libraries, runtime APIs, or device launch
  - is binding-owned integration work, not pass/runtime-core semantics

- **Build/materialization**
  - prepares backend artifacts for later execution
  - may produce shared libraries, `.ptx`, `.cubin`, or other binaries
  - must keep authoritative HTP source/package artifacts intact

---

## 2) Binding selection

`bind(package_dir)` selects a binding plugin based on:

- `manifest.target.backend` (`pto`, `aie`, ...)
- `manifest.target.variant` (optional)
- and optional binding overrides (developer tooling)

The binding must refuse to run if:

- required files are missing from the artifact contract, or
- required toolchain/runtime contracts are not satisfied.

---

## 3) Minimal API surface (normative v1)

The binding API is part of the design surface. V1 should standardize these operations:

- `binding = htp.bind(package_dir, binding_override=None)`
- `report = binding.validate()`
- `build = binding.build(mode="sim"|"device", force=False, cache_dir=None)`
- `session = binding.load(mode="sim"|"device")`
- `result = session.run(entry, *, args=(), kwargs=None, trace="off"|"basic"|"full")`
- `result = session.replay(stage_id, *, entry=None, args=(), kwargs=None, mode="sim", trace="basic")`

Notes:

- `mode="sim"` uses backend simulators where possible (e.g. `pto-runtime` `a2a3sim`).
- `mode="device"` uses device runtimes/toolchains and may require environment setup.
- stages always provide `program.py` and are runnable in `mode="sim"` (possibly stubbed with explicit diagnostics).
- for backend packages, `run()` is binding-owned:
  - PTO maps the package into the `pto-runtime` compile/load/run surface for both `a2a3sim` and `a2a3`
  - NV-GPU maps the package into a binding-owned execution adapter (`nvcc`, `nvrtc`, loader, launch wrapper, profiler)
  - `htp.runtime` remains the replay/runtime surface for stage programs, not the owner of external execution integration

### 3.1 Return records

`validate()` returns:

- `ok: bool`
- `backend`
- `variant`
- `diagnostics[]`
- `missing_files[]`
- `contract_refs[]`

`build()` returns:

- `ok: bool`
- `mode`
- `built_outputs[]`
- `log_paths[]`
- `diagnostics[]`

`run()` / `replay()` return:

- `ok: bool`
- `mode`
- `entry`
- `result_ref` or inline scalar result
- `trace_ref`
- `diagnostics[]`
- `stage_id` (for replay)

Bindings may add backend-specific fields under a namespaced extension object, but the fields above must always exist.

For v1 specifically:

- NV-GPU `build()` reports the emitted `.cu` source, launch Python, codegen index, toolchain manifest, and any declared
  derived outputs; `build(mode="device")` is the point where those derived outputs are materialized through `nvcc`.
- PTO `build()` reports the materialized `build/pto/` outputs produced through `pto-runtime` (`libhost_runtime.so`,
  `libaicpu_runtime.so`, `aicore_runtime.bin`, orchestration `.so`, per-kernel binaries).

The broader rule is:

- authoritative HTP artifacts are source/package-facing,
- derived toolchain artifacts are build-facing,
- both are visible through normalized result records.

---

## 4) Validation and diagnostics contract

Validation returns a structured report:

- missing required files (artifact contract violations)
- toolchain/runtime contract mismatches
- entrypoint signature mismatches

Run/replay failures must emit:

- stable diagnostic codes,
- node ids (when source-level blame is possible),
- and file pointers to relevant stage dumps and logs.

For replay-time stub hits, bindings should surface structured replay
diagnostics rather than raw runtime exceptions.

---

## 5) Logs and run records

Bindings now write structured log payloads into the package:

```
logs/
  build_<backend>_<mode>_<ts>.log
  run_<backend>_<mode>_<ts>.log
  trace_<backend>_<ts>.jsonl          # optional structured runtime trace
```

Each `.log` file is now a JSON payload with schema `htp.binding_log.v1` and
normalized `kind` / `fields` content, rather than ad-hoc text lines.

and record the paths in `manifest.outputs` or `manifest.extensions.<backend>`.

Bindings should also emit:

```
logs/
  replay_<stage_id>_<mode>_<ts>.log     # when replay is invoked
```

and surface the corresponding path in the replay result record.

The current implementation also keeps:

- `ReplayResult.log_path`
- `RunResult.log_path`
- `BuildResult.log_paths`

as the stable API surface for these files.

For real external execution, bindings should also surface enough information to reconstruct the adapter path that was
used, for example:

- selected toolchain/runtime mode,
- selected adapter (`nvcc`, `nvrtc`, `pto-runtime`, etc.),
- and relevant emitted binary paths when materialized.

The current v1 adapters are:

- PTO: `pto-runtime` builder/compiler/bindings integration,
- NV-GPU: `nvcc` for build materialization and a minimal CUDA driver loader for device launch.

---

## 6) Replay semantics (stage programs are the contract)

Replaying a stage means:

- import and execute `ir/stages/<stage_id>/program.py`, not an internal IR interpreter.
- honor the stage’s declared `RunnablePy` contract:
  - `preserves`: stage is runnable in the declared modes
  - `stubbed`: runnable but calls stubs for some regions (must have stub metadata + explicit diagnostics)
  - invariant: stages are always runnable in `mode="sim"`; missing `program.py` is a contract violation

This is how HTP keeps debugging stable across refactors: replay is a file contract, not a private API.

---

## 7) Surfacing analysis results (developer ergonomics)

Bindings should treat analyses as first-class debug data:

- stage-local analysis results live under `ir/stages/<id>/analysis/`
- `analysis/index.json` enumerates available analyses, versions, and schemas

When a runtime failure occurs, the binding should include pointers to:

- relevant stage programs (`program.py`)
- relevant analyses that justify the applied transforms (e.g., pipelining plans)
- relevant build/run logs

This is essential for long-term agentic development: failures must be localizable to a contract boundary with evidence.
