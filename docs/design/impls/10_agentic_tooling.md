# Impl: Agent-Facing Tooling

Current code anchors:

- tool APIs: `htp/tools.py`
- CLI: `htp/__main__.py`
- policy loading: `htp/agent_policy.py`
- diagnostic catalog: `htp/diagnostics.py`
- package export: `htp/__init__.py`
- tests: `tests/tools/test_tools.py`, `tests/tools/test_cli.py`

Implemented commands:

- `htp replay <package>`
- `htp verify <package>`
- `htp diff --semantic <left> <right>`
- `htp explain <diagnostic-code>`
- `htp bisect <left> <right>`
- `htp minimize <package> <output-dir>`
- diagnostic explanations are served from `htp/diagnostics.py`

Implemented provenance:

- `verify_package(...)` records:
  - `extensions.agent.run_id`
  - `extensions.agent.goal`
  - `extensions.agent.gates`
  - `extensions.agent.evidence`
  - `extensions.agent.policy`
  - `extensions.agent.patch_summary`
  - `extensions.agent.decision_trace`
  - `extensions.agent.attempted_candidates`
  - `extensions.agent.rejected_candidates`

Current scope:

- artifact-driven tooling only
- no autonomous patch loop in core
- reducer/minimizer is stage-prefix package pruning, not semantic delta minimization
- semantic diff now includes section-level difference summaries, but not identity-aware diffs yet
- `verify_package(...)` can enforce an optional golden semantic-diff gate
