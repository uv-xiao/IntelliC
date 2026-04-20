# IntelliC Agent Guide

This file is the Codex entrypoint for the clean IntelliC branch.

## Read First

Before editing, agents must:

1. run `git status --short --branch`
2. read `.agents/README.md`
3. read all files under `.agents/rules/`
4. load any task-relevant skill under `.agents/skills/<name>/SKILL.md`
5. inspect relevant docs under `docs/design/`, `docs/todo/`, and `docs/in_progress/`

## Harness Layout

- `.agents/rules/`: persistent project rules
- `.agents/skills/`: executable workflows
- `.agents/agents/`: expert consultation profiles
- `.agents/templates/`: reusable task, design, PR, and review templates

Do not create or depend on `.codex/`, `.claude/`, or `.opencode/` in this clean branch.
