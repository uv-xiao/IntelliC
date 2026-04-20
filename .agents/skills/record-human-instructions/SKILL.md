---
name: record-human-instructions
description: Record human/user instructions into a repository's docs/in_progress/human_words/ directory with category grouping and chronological timeline ordering. Use when a user asks to record, preserve, capture, organize, or archive human wording, requirements, feedback, rules, constraints, or design directives for active work.
---

# Record Human Instructions

## Goal

Preserve source human wording during active work without turning every statement into a project rule. Record exact instructions under `docs/in_progress/human_words/`, grouped by category and ordered by timeline; promote only curated decisions into rules, task files, or design docs.

## Workflow

1. Find the repository root with `git rev-parse --show-toplevel` when available.
2. Read `docs/in_progress/human_words/README.md` if present, then inspect existing category files with `find docs/in_progress/human_words -maxdepth 1 -type f | sort`.
3. Choose the narrowest useful category. Prefer existing category names; otherwise use clear names such as `Agent Harness`, `Compiler Framework`, `Syntax`, `Semantics`, `Passes`, `Docs And Knowledge`, `Verification`, or `Other`.
4. Preserve the user's wording exactly or as close as the transcript allows. Put any agent interpretation in a separate field.
5. Record entries in chronological order inside the category file. If several instructions have the same date, preserve conversation order.
6. Verify by rereading the changed file and checking that the category, date, context, related docs, and exact wording are present.

Documentation-only recording does not require automated tests. Use a focused reread, path check, or repo policy check when available.

## Preferred Script

Use the bundled project script for consistent files:

```bash
python .agents/skills/record-human-instructions/scripts/record_human_instruction.py \
  --repo-root . \
  --category "Agent Harness" \
  --event "Human instruction recording rule" \
  --instruction "Add a new agent rules: record human instructions under @docs/in_progress/human_words/ ." \
  --context "User updated agent harness rules during active design work." \
  --related ".agents/rules/docs-and-knowledge.md" \
  --interpretation "Record source wording under docs/in_progress/human_words/ before promoting curated rules elsewhere."
```

The script creates or updates `docs/in_progress/human_words/<category-slug>.md`, appends the timeline entry, and sorts entries by timestamp.

Use `--instruction-file <path>` instead of `--instruction` when the wording is multiline or shell quoting would be fragile.

## Manual Format

If the script is unsuitable, edit with the same shape:

```markdown
# Human Words: <Category>

## Category

- Primary: <Category>

## Timeline

- YYYY-MM-DD HH:MM <timezone> - <short event>
  > <human wording>
  - Context: <where this instruction appeared>
  - Related: <docs or files affected>
  - Agent interpretation: <non-normative interpretation>
```

Keep category files readable. Do not mix unrelated topics just to reduce file count.

## Examples

User says: `Add a new agent rules: record human instructions under @docs/in_progress/human_words/ .`

Record under category `Agent Harness` with the exact sentence quoted, related to `.agents/rules/docs-and-knowledge.md` and `docs/in_progress/human_words/README.md`.

User says: `surface parser should also be modular, but can share a common infrastructure.`

Record under category `Compiler Framework` or `Syntax`, then update the relevant design doc only after deciding the curated architecture wording.
