# Agent Product and Repository Workflow

This document describes the implemented agent-facing surface and the repository workflow that supports controlled development.

## Why this topic exists

HTP treats agent-based compiler development as a native target. That means two things in practice:
- emitted compiler artifacts must be stable and inspectable enough for machine-guided debugging and regression localization
- the repository workflow itself must make implemented work, pending work, and active work explicit, and the critical parts of that workflow must be machine-enforceable

The current repository now has a real operational model for that.

## Visual model

```text
docs/todo -> feature branch -> docs/in_progress -> PR -> docs/design
```

```text
package -> verify -> promotion bundle -> workflow report
```

```text
changed files -> edit-corridor evaluation -> CI / local policy check
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
- `htp policy-check`
- `htp workflow-state`

Supporting policy/config surfaces include:
- `htp/agent_policy.py`
- `agent_policy.toml`
- PR template enforcement
- branch and PR policy checks
- task-file workflow under `docs/in_progress/`

## Implemented workflow controls

The repository now enforces a concrete operating model:
- `examples/` is an allowed edit root because flagship examples are part of the proof surface, not optional documentation
- `htp/dev` is the stable branch
- feature work happens on `htp/feat-*`
- each PR-sized task starts with a task file under `docs/in_progress/`
- landed behavior belongs in `docs/design/`
- open future work belongs in `docs/todo/`
- completed task files must be removed before merge
- edit corridors are evaluated against the changed file set and require matching tests/docs for active contract surfaces
- `verify` records a promotion-gate bundle and a workflow report into the package so later automation can consume the same evidence

## Why this matters technically

Replayable artifacts and stable diagnostics are what let an agent localize problems. The branch/task/docs workflow is what keeps that development healthy instead of allowing uncontrolled drift. The new corridor evaluation and workflow-state inspection close the gap between documented process and machine-visible process.

In other words, the repository workflow is not separate from the product goal. It is part of how HTP tries to stay evolvable under long-term human + agent development.

## Coding pointers

Relevant code and policy files:
- `htp/agent_policy.py`
- `htp/tools.py`
- `htp/__main__.py`
- `agent_policy.toml`
- `AGENTS.md`
- `.agent/rules/`
- `.github/scripts/check_pr_policy.py`
- `.github/pull_request_template.md`

## Status

This topic is currently closed in `docs/todo/`. Future work in this area should reopen `docs/todo/` only when there is a concrete new automation or workflow control that is not already represented by the current tool and CI surface.
