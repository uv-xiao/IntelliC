---
name: clean-branches
description: "Find and remove stale local and remote git branches after classifying whether they are merged, squash-merged, gone, protected, or unfinished. Use when the user asks to clean branches, remove useless branches, prune stale refs, delete merged feature branches, or tidy local and fork remote branch state."
---

# Clean Branches

Use this to remove useless git branches without deleting active work. The model is adapted from pypto's `clean-branches` skill: discover first, classify carefully, show a deletion plan, then delete only after explicit user approval.

## Safety Rules

- Never delete `main`, `HEAD`, the current branch, or protected release/base branches.
- Never delete remote branches from an upstream/shared remote unless the user explicitly names that remote and confirms it.
- Prefer cleaning the fork remote, usually `origin`.
- Never delete branches before showing the candidate table and receiving explicit approval.
- Treat branch tips that differ from a merged PR head as unfinished work.
- If `gh` is unavailable, say squash-merge detection is limited and use only git evidence.
- Use `git branch -d` for normally merged local branches; use `git branch -D` only for approved squash-merged or explicitly selected branches.

## Workflow

1. Confirm the repo and current branch:

   ```bash
   git status --short --branch
   git remote -v
   git branch --all --verbose --no-abbrev
   ```

2. Identify remotes:

   - `origin` is usually the user's fork or primary writable remote.
   - `upstream` or organization remotes are shared remotes and are not deletion targets by default.
   - If unclear, ask which remote is safe to clean before deleting remote branches.

3. Refresh refs without deleting anything:

   ```bash
   git fetch --all --prune --dry-run
   git remote prune <fork> --dry-run
   ```

4. Gather candidates:

   ```bash
   git branch --merged main
   git branch --format='%(refname:short) %(objectname) %(upstream:short) %(upstream:track)'
   git branch -r --format='%(refname:short) %(objectname)' --list '<fork>/*'
   ```

   Exclude protected names such as `main`, `HEAD`, `master`, `develop`, `release/*`, `stable/*`, and the current branch unless the user explicitly says otherwise.

5. Classify each candidate:

   | Category | Evidence | Default action |
   | --- | --- | --- |
   | `merged` | `git branch --merged main` contains the branch | Safe candidate |
   | `squash-merged` | `gh pr list --head <branch> --state merged` finds a PR and branch tip equals `headRefOid` | Safe candidate |
   | `gone-upstream` | Local branch tracks a deleted remote and has no unique commits against `main` | Safe candidate |
   | `remote-only-merged` | Remote branch has merged PR evidence or is ancestor of `main` | Safe candidate |
   | `unfinished` | No merge evidence or branch tip changed after merged PR | Keep by default |
   | `protected` | Main/base/release/current/upstream branch | Never delete by default |

6. Detect squash-merged branches when `gh` exists:

   ```bash
   gh pr list --head "<branch-name>" --state merged --json number,title,headRefOid,mergedAt --limit 1
   ```

   For remote branches, strip the `<fork>/` prefix before querying. Compare the branch tip SHA to `headRefOid`; if they differ, mark the branch as `unfinished`.

7. Present a plan:

   ```text
   Safe deletion candidates:
   | # | Branch | Local | Remote | Category | Evidence |
   |---|--------|-------|--------|----------|----------|

   Kept branches:
   | # | Branch | Local | Remote | Category | Reason |
   |---|--------|-------|--------|----------|--------|
   ```

8. Ask for explicit approval. Good options:

   - Delete safe candidates only.
   - Delete selected branches only.
   - Dry-run commands only.
   - Stop without deletion.

9. Delete only approved branches:

   ```bash
   git branch -d <merged-local-branch>
   git branch -D <approved-squash-or-selected-local-branch>
   git push <fork> --delete <approved-remote-branch>
   git remote prune <fork>
   ```

10. Report exact results: deleted local branches, deleted remote branches, pruned refs, kept branches, and any errors.

## Examples

User asks: `Clean up merged branches.`

Action: classify local and fork remote branches, show safe candidates, request approval, then delete only approved merged or squash-merged branches.

User asks: `Remove every branch except main.`

Action: show all non-protected branches including unfinished ones, warn that unfinished work may be lost, require explicit confirmation, and never delete shared upstream branches by default.

User asks: `Prune stale refs.`

Action: run `git remote prune <fork> --dry-run`, show stale tracking refs, ask approval, then run `git remote prune <fork>`.
