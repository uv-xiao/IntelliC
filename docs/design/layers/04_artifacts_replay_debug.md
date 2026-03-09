# Layer 4 — Artifacts, Replay, and Debugging

This layer describes the package contract that makes HTP inspectable.

## Narrative

HTP is artifact-first. Compilation emits a package with staged IR, backend codegen, build outputs, logs, and diagnostics. Replay is distinct from backend execution: replay runs staged Python in `sim`, while bindings own validate/build/load/run for emitted backend packages.

The current implementation already has:
- normalized `manifest.json`
- staged IR under `ir/stages/`
- structured `ir/pass_trace.jsonl`
- structured binding logs and adapter traces
- replay stub diagnostics with doc references and fix-hint policies
- CLI/tool support for replay, verify, semantic diff, explain, minimize, bisect, and promote-plan

## Visual model

```text
package/
  manifest.json
  ir/stages/*
  codegen/<backend>/*
  build/*
  logs/*
```

```text
replay(package) -> staged Python + sim runtime
run(package)    -> binding + backend adapter
```

## Implemented contracts

- emitted files are normative contract surfaces
- malformed packages must fail with structured diagnostics, not opaque crashes
- replay evidence, binding logs, and adapter traces are part of the observable debugging surface
- semantic diff uses stage sidecars, ids, maps, and pass traces rather than textual guesswork

## Main code anchors

- `htp/artifacts/manifest.py`
- `htp/artifacts/validate.py`
- `htp/runtime/core.py`
- `htp/runtime/errors.py`
- `htp/bindings/validate.py`
- `htp/tools.py`
- `htp/diagnostics.py`
- `htp/__main__.py`
