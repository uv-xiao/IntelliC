# Layer 6 — Agent Product and Repository Workflow

This layer describes the implemented agent-facing product and the repository operating model.

## Narrative

HTP treats agent development as a first-class target. That does not only mean adding an `agent_policy.toml`; it means the repository and artifact surfaces are shaped so an agent can inspect, replay, diff, verify, and narrow changes with explicit evidence.

The implemented agent product includes:
- `htp replay`
- `htp verify`
- `htp diff --semantic`
- `htp explain`
- `htp bisect`
- `htp minimize`
- `htp promote-plan`
- structured edit-corridor templates in `htp/agent_policy.py`

The repository workflow is also part of the product:
- `htp/dev` is stable
- feature work happens on `htp/feat-*`
- `docs/in_progress/` tracks active PR-sized work
- `docs/design/` holds landed behavior
- `docs/todo/` holds remaining work

## Visual model

```text
TODO -> feature branch -> docs/in_progress -> PR -> docs/design
```

```text
package -> replay/verify/diff/explain -> agent evidence
```

## Implemented contracts

- task files are the first commit on a feature branch
- PRs must use the repo template
- CI/policy checks are part of the controlled development loop
- agent guidance forbids low-signal tests, weak CI fixes, and unreadable flagship examples

## Main code anchors

- `htp/agent_policy.py`
- `AGENTS.md`
- `.agent/rules/`
- `.github/scripts/check_pr_policy.py`
- `.github/pull_request_template.md`
