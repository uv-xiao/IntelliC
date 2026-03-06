# Impl: Binding Interface (compile → bind → run → replay)

## Goal

Standardize `bind(package)` so users get a consistent experience across backends, while preserving backend-specific
build/run realities.

Bindings are also the execution substrate for:

- staged replay (`RunnablePy`) in `sim|device` modes,
- artifact contract validation,
- and trace/log collection.

---

## 1) Binding lifecycle

1) **Validate**: validate package + manifest against backend artifact contract.
2) **Build** (optional): invoke toolchains to produce runnable binaries from `codegen/<backend>/...` sources/recipes.
3) **Load**: load runtime handles (shared libraries, device runners, simulators).
4) **Run**: execute entrypoints with typed marshalling and trace hooks.
5) **Replay**: execute a specific stage’s `ir/stages/<id>/program.py` (always runnable in `mode="sim"`; may be stubbed).
6) **Report**: emit structured run records, diagnostics, and log pointers into the package.

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

## 3) Minimal API surface (illustrative)

Conceptual API (exact names not important; semantics are):

- `binding = htp.bind(package_dir)`
- `report = binding.validate()`
- `build = binding.build(mode="sim"|"device", force=False, cache_dir=None)`
- `session = binding.load(mode="sim"|"device")`
- `result = session.run(entry="main", args=[...], trace="off"|"basic"|"full")`
- `result = session.replay(stage_id="s02", entry="main", args=[...], mode="sim")`

Notes:

- `mode="sim"` uses backend simulators where possible (e.g. `pto-runtime` `a2a3sim`).
- `mode="device"` uses device runtimes/toolchains and may require environment setup.
- `replay(stage_id=...)` requires that stage provides `program.py` (pass contract `RunnablePy`).

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

---

## 5) Logs and run records

Bindings should write into the package:

```
logs/
  build_<backend>_<mode>_<ts>.log
  run_<backend>_<mode>_<ts>.log
  trace_<backend>_<ts>.jsonl          # optional structured runtime trace
```

and record the paths in `manifest.outputs` or `manifest.extensions.<backend>`.

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
