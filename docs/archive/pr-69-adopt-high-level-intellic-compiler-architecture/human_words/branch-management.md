# Human Words: Branch Management

## Category

- Primary: Branch Management

## Timeline

- 2026-04-21 02:35 Asia/Shanghai - Rename clean branch to main
  > Let's also rename the branch to just "main" and push.
  - Context: User requested renaming the current clean IntelliC branch and pushing it to origin.
  - Related: git branch -m main
  - Related: git push -u origin main
  - Agent interpretation: Preserve any pre-existing local main branch before moving the current branch to main, then push main with upstream tracking.

- 2026-04-21 02:44 Asia/Shanghai - Approve safe branch cleanup
  > 1
  - Context: User selected option 1 from clean-branches approval prompt, meaning delete safe candidates only.
  - Related: .agents/skills/clean-branches/SKILL.md
  - Agent interpretation: Delete only branches classified as safe candidates; keep backup, protected, unfinished, and needs-review branches.
