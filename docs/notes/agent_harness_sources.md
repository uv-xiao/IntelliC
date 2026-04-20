# Agent Harness Source Reading Report

- **Date**: 2026-04-20
- **Purpose**: Extract durable agent-harness practices for the clean ICI branch.

## Sources

- `.references/areal-vibe.pdf`
- `https://www.inclusion-ai.org/AReaL/en/reference/ai_assisted_dev.html`
- `.repositories/AReaL`
- `.repositories/pypto`
- `.repositories/simpler`
- `origin/htp/v0`

## Extracted Lessons

- Keep root agent instructions short and route detailed guidance into smaller files.
- Use rules, skills, expert profiles, and design docs as persistent cross-session memory.
- Require explicit input, output, and verification criteria for every feature task.
- Treat evidence, minimal demos, and tests as the contract between human and agent.
- Keep local reference PDFs and cloned repositories ignored; commit only curated reading reports.
- Preserve the v0 docs lifecycle: active drafts in `docs/in_progress/`, implemented design in `docs/design`, and open gaps in `docs/todo/`.

## Decisions Affected

- Use `.agents/` as the only repo-local agent harness directory.
- Use `docs/notes/` for all document and repository reading reports.
- Ban `.codex/`, `.claude/`, and `.opencode/` from the clean branch scaffold.
- Add policy checks for harness shape and stale in-progress design drafts.
