# Agent Product and Repository Workflow

This document describes the implemented agent-facing surface and the repository workflow that supports controlled development.

## Why this topic exists

HTP treats agent-based compiler development as a native target. That means two things in practice:
- emitted compiler artifacts must be stable and inspectable enough for machine-guided debugging and regression localization
- the repository workflow itself must make implemented work, pending work, and active work explicit

The current repository now has a real operational model for that.

## Visual model

```text
docs/todo -> feature branch -> docs/in_progress -> PR -> docs/design
```

```text
package -> replay / verify / diff / explain / bisect / minimize
```

## Implemented product surface

The current agent-facing tools include:
- `htp replay`
- `htp verify`
- `htp diff --semantic`
- `htp explain`
- `htp bisect`
- `htp minimize`
- `htp promote-plan`

Supporting policy/config surfaces include:
- `htp/agent_policy.py`
- PR template enforcement
- branch and PR policy checks
- task-file workflow under `docs/in_progress/`

## Implemented repository workflow

The repository now enforces a cleaner operating model:
- `htp/dev` is the stable branch
- feature work happens on `htp/feat-*`
- each PR-sized task starts with a task file under `docs/in_progress/`
- landed behavior belongs in `docs/design/`
- remaining work belongs in `docs/todo/`
- completed task files must be removed before merge

## Why this matters technically

Replayable artifacts and stable diagnostics are what let an agent localize problems. The branch/task/docs workflow is what keeps that development healthy instead of allowing uncontrolled drift.

In other words, the repository workflow is not separate from the product goal. It is part of how HTP tries to stay evolvable under long-term human + agent development.

## Coding pointers

Relevant code and policy files:
- `htp/agent_policy.py`
- `htp/tools.py`
- `htp/diagnostics.py`
- `AGENTS.md`
- `.agent/rules/`
- `.github/scripts/check_pr_policy.py`
- `.github/pull_request_template.md`

## Current limits

The repository workflow is now much cleaner, but the full autonomous-development target still extends beyond the current implementation. The remaining work lives in `docs/todo/agent_product_and_workflow.md`.
