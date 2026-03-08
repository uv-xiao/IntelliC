# Impl: Agent-Facing Tooling

Current code anchors:

- tool APIs: `htp/tools.py`
- CLI: `htp/__main__.py`
- package export: `htp/__init__.py`
- tests: `tests/tools/test_tools.py`, `tests/tools/test_cli.py`

Implemented commands:

- `htp replay <package>`
- `htp verify <package>`
- `htp diff --semantic <left> <right>`
- `htp explain <diagnostic-code>`
- diagnostic explanations are served from `htp/diagnostics.py`

Implemented provenance:

- `verify_package(...)` records:
  - `extensions.agent.run_id`
  - `extensions.agent.goal`
  - `extensions.agent.gates`
  - `extensions.agent.evidence`

Current scope:

- artifact-driven tooling only
- no autonomous patch loop in core
- no reducer/minimizer yet
