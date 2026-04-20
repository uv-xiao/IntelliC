# Agent Harness

This document describes the implemented clean-branch agent harness.

## Implemented Structure

- `AGENTS.md` is the Codex entrypoint and router.
- `.agents/rules/` holds mandatory project rules.
- `.agents/skills/` holds executable repo workflows.
- `.agents/agents/` holds expert consultation profiles.
- `.agents/templates/` holds reusable task, design, PR, and review templates.

## Rationale

The harness keeps root context short and stores durable project memory in small,
targeted files. It adopts AReaL's rules/skills/agents layering, PyPTO's
workflow discipline, Simpler's environment isolation, and v0's strict docs
lifecycle without bringing over legacy compiler implementation.

## Code Pointers

- `AGENTS.md`
- `.agents/README.md`
- `.agents/rules/`
- `.agents/skills/`
- `scripts/check_repo_harness.py`
