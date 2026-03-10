# HTP Agent Guidance

This directory holds reduced, HTP-specific guidance for automated development.

Read in this order:

1. `.agent/rules/core-development.md`
2. `.agent/rules/docs-and-artifacts.md`
3. `.agent/rules/testing-and-verification.md`

The repo-wide default contract lives in `AGENTS.md`.

Operational intent:
- choose work from `docs/todo/README.md`
- track active feature branches in `docs/in_progress/`
- document landed behavior in `docs/design/`
- keep Python AST canonical and replayable in `sim`
- keep examples, tests, and code human-readable
- keep `htp/dev` stable through feature branches and green PRs
