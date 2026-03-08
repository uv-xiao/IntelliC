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
- keep bindings and backends explicit and testable,
- keep `htp/dev` stable and do feature work on `htp/feat-*` branches,
- keep `docs/design/` implemented-only and `docs/future/` future-only.

The repo-wide default guidance now lives in `AGENTS.md`.
