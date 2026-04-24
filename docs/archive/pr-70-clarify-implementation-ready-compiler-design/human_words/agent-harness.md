# Human Words: Agent Harness

## Category

- Primary: Agent Harness

## Timeline

- 2026-04-24 11:09 CST - Archive human words after PR merge
  > create an agent rule (and skill if needed): when doing PR merging, we need to move docs/in_progress/human_words to the docs/archive folder, with a name generated to represent the PR they come from. Apply this rule after creating it for the PR merged before.
  - Context: User requested a persistent PR-merge documentation lifecycle rule and asked to apply it retroactively to the previously merged PR.
  - Related: .agents/rules/docs-and-knowledge.md
  - Related: .agents/rules/development-flow.md
  - Related: .agents/skills/merge-pr/SKILL.md
  - Related: docs/archive/pr-69-adopt-high-level-intellic-compiler-architecture/human_words/
  - Agent interpretation: During PR merge cleanup, archive the closed PR's captured human wording under a PR-derived docs/archive folder and leave docs/in_progress/human_words ready for new active work.
