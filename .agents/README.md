# IntelliC Agent Harness

The harness is intentionally repo-local and Codex-readable through `AGENTS.md`.

## Principles

- keep root instructions short
- route detailed guidance into rules, skills, agents, and docs
- require evidence before completion claims
- prefer small plans with explicit verification over broad implementation prompts
- keep `.references/` and `.repositories/` ignored and local

## Layout

- `rules/`: mandatory project rules
- `skills/`: workflows agents can execute directly
- `agents/`: expert profiles for consultation
- `templates/`: standard document shapes
