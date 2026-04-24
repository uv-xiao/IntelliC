# Human Words: Agent Harness

## Category

- Primary: Agent Harness

## Timeline

- 2026-04-21 02:10 Asia/Shanghai - Initial repo setup and harness request
  > Good. Now we have a brand new repo. We should start now by first create agent harness. I've create the .references, which include .references/areal-
  >   vibe.pdf that give many advice for agent harness (clone git@github.com:inclusionAI/AReaL.git into .repositories to learn details, https://www.inclusion-
  >   ai.org/AReaL/en/reference/ai_assisted_dev.html has a short description, we only do codex related setup, but prefer .agents/ and AGENTs.md , don't
  >   use .codex/). You should also clone https://github.com/hw-native-sys/pypto and https://github.com/hw-native-sys/simpler into .repositories/, both of which
  >   have agent rules and skills to learn. For the first commits, we need to build the file structure, rules, skills, and the organization for this project.
  >   You should also absorb experience from dev/v0 branch, where how docs/ directory is used is specified. Give a plan under docs/in_progress/repo_setup.md
  >   first to list all things to add.
  - Context: User directed the initial clean-repo agent harness setup before the current harness structure existed.
  - Related: AGENTS.md
  - Related: .agents/
  - Related: docs/in_progress/repo_setup.md
  - Related: docs/notes/agent_harness_sources.md
  - Agent interpretation: Build a repo-local Codex-readable harness, learn from referenced repositories and v0 docs lifecycle, avoid `.codex/`, and start with an in-progress setup plan.

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

- 2026-04-21 02:37 Asia/Shanghai - Clean-branches skill request
  > Create a skill $skill-creator under this repository. Learn from .repositories/pypto/.claude/skills/clean-branches/SKILL.md, I want the skill to remove useless local and remote branches.
  - Context: User requested a repo-local skill for cleaning useless local and remote git branches, using skill-creator and pypto's clean-branches skill as reference.
  - Related: .agents/skills/clean-branches/SKILL.md
  - Related: .repositories/pypto/.claude/skills/clean-branches/SKILL.md
  - Agent interpretation: Create a local clean-branches workflow that discovers stale branches, classifies safe deletion candidates, requires explicit approval, deletes only approved local and fork remote branches, and prunes refs.

- 2026-04-21 02:40 Asia/Shanghai - Clean-branches YAML fix
  > fix:  /home/uvxiao/htp/.agents/skills/clean-branches/SKILL.md: invalid YAML: description: invalid type: sequence, expected a string at line 2 column 14
  - Context: User reported strict YAML parsing failure in the new clean-branches skill frontmatter.
  - Related: .agents/skills/clean-branches/SKILL.md
  - Agent interpretation: Quote the skill description so all YAML parsers treat it as an explicit string.
