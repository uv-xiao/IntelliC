# HTP Agent Guidance

This directory holds reduced, HTP-specific guidance for automated development.

Read in this order:

1. `.agent/rules/core-development.md`
2. `.agent/rules/docs-and-artifacts.md`
3. `.agent/rules/testing-and-verification.md`

Use the skills under `.agent/skills/` when the task is specifically about review or verification.

The intent is narrow:

- keep Python AST canonical,
- keep stage artifacts contractual,
- keep replay in `sim` runnable,
- keep bindings and backends explicit and testable.

## Commands

- `.agent/commands/init.md` — strict repo initialization and coding guidance for any new agent session
