# Agent Workflow Closure

- ID: `022-agent-workflow-closure`
- Branch: `htp/feat-agent-workflow-closure`
- PR: `#57`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Close the remaining agent-product and repository-workflow gap by making key workflow constraints machine-enforceable. The implementation adds explicit edit-corridor evaluation, persisted promotion/workflow evidence, and workflow-state inspection so the repository process is enforced by code and CI rather than only by prose.

## Why

- contract gap: the last open TODO topic is `docs/todo/agent_product_and_workflow.md`, and the missing part is machine enforcement of workflow obligations
- user-facing impact: agents and contributors can inspect workflow state and policy failures directly instead of reconstructing them manually
- architectural reason: HTP claims agent-native development as part of the product, so workflow discipline must live in the same contract surface as replay, diagnostics, and package evidence

## Scope Checklist

- [x] make edit-corridor policy enforceable in tooling and PR policy
- [x] add bundled promotion-gate evaluation and persisted workflow evidence
- [x] expose workflow-state inspection in the CLI/tool surface
- [x] tighten docs and repo policy around the machine-enforced workflow
- [x] close the remaining `docs/todo/` topic and sync summary counts to zero open items

## Code Surfaces

- producer: `htp/tools.py`, `htp/__main__.py`
- validator/binding: package workflow-report emission through `verify_package`
- tests: `tests/tools/test_tools.py`, `tests/test_pr_policy_script.py`, `tests/test_docs_layout.py`
- docs: `docs/design/agent_product_and_workflow.md`, `docs/todo/README.md`, `README.md`, `AGENTS.md`, `.agent/rules/*`

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added (CLI/doc workflow surface and package workflow report evidence)
- [x] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete workflow-control or promotion contract.

## Documentation Plan

- [x] update `docs/design/` for implemented workflow controls
- [x] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. add focused tests for workflow-control and promotion-bundle contracts
3. land agent-policy, tool, and CI-policy updates
4. sync docs and close the TODO tree
5. rebase, review, and merge

## Review Notes

Reviewers should check that workflow enforcement remains generic and repository-scoped: no backend-specific behavior should leak into the agent-policy or PR-policy logic.
