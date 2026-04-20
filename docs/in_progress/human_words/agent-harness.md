# Human Words: Agent Harness

## Category

- Primary: Agent Harness

## Timeline

- 2026-04-21 02:15 Asia/Shanghai - Human instruction recording rule
  > Add a new agent rules: record human instructions under @docs/in_progress/human_words/ .
  - Context: User added a persistent agent harness rule during active IntelliC design work.
  - Related: .agents/rules/docs-and-knowledge.md
  - Related: docs/in_progress/human_words/README.md
  - Agent interpretation: Record source human wording under docs/in_progress/human_words/ during active work before promoting curated decisions elsewhere.

- 2026-04-21 02:15 Asia/Shanghai - Record-human-instructions skill request
  > $skill-creator create a skill to record human instructions as the agent rule requires. You should do category and timeline ordering for the recording.
  - Context: User invoked skill-creator to create a reusable skill for the new human instruction recording rule.
  - Related: .agents/skills/record-human-instructions/SKILL.md
  - Related: docs/in_progress/human_words/agent-harness.md
  - Agent interpretation: Create a Codex skill that records instructions by category and maintains chronological timeline ordering.

- 2026-04-21 02:25 Asia/Shanghai - Project rename and local skill request
  > Let's do a rename again. The project should be named IntelliC (or intellic, or ic for very short), which represent intelligent compiler. Let's create commits for all updates. But very seriously, the design commit should mark the things as not reviewed and approved. Also, the record human instructions skill should be triggered before making the commits, especially about how this project is for and the design with fix advice. The skill should be moved into this project, since it's a local one.
  - Context: User requested project naming, commit creation, design-draft caution, localizing the human-instruction recording skill, and recording the instruction before committing.
  - Related: docs/in_progress/human_words/agent-harness.md
  - Related: .agents/skills/record-human-instructions/SKILL.md
  - Agent interpretation: Rename project references from ICI to IntelliC/intellic/ic where appropriate, move the recording skill into the project harness, and make design drafts explicitly unreviewed/unapproved before committing.
