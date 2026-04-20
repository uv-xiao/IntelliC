# Repo Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first clean-branch repository scaffold for ICI: agent harness, development rules, skills, docs organization, and policy checks before any compiler implementation begins.

**Architecture:** Keep the root instructions small and route deeper guidance through `.agents/`. Use `AGENTS.md` as the Codex entrypoint, `.agents/rules/` for always-on and scoped rules, `.agents/skills/` for executable workflows, and `.agents/agents/` for expert consultation profiles. Preserve the v0 docs lifecycle shape (`docs/design`, `docs/todo`, `docs/in_progress`, `docs/story.md`) while starting from a clean, minimal tree.

**Tech Stack:** Markdown, Python stdlib policy scripts, GitHub Actions, Codex-compatible repo-local skills, no `.codex/` directory.

---

## Source Inputs Reviewed

- `.references/areal-vibe.pdf`
  - planning is the highest-leverage agent activity
  - every subtask needs explicit input, output, and verification criteria
  - evidence and minimal demos must drive long-running implementation and debugging
  - rules, agents, skills, and design docs form persistent cross-session memory
  - dynamic review and verification are quality gates, not optional polish
- `https://www.inclusion-ai.org/AReaL/en/reference/ai_assisted_dev.html`
  - Codex reads `AGENTS.md`
  - directly executable Codex workflows can live under `.agents/skills/<name>/SKILL.md`
  - AReaL uses `.codex/` for Codex custom-agent registration, but ICI clean will not use `.codex/`
- `.repositories/AReaL`
  - concise `AGENTS.md` as router
  - `.agents/skills/` for repeatable workflows such as `create-pr`, `review-pr`, and `add-unit-tests`
  - domain experts and review/verifier roles as explicit harness concepts
- `.repositories/pypto`
  - Codex entrypoint can route into a separate rule/skill tree
  - cross-layer sync, testing workflow, code review, commit workflow, and docs placement rules are worth adopting
  - no AI co-author lines in commits or PR text
- `.repositories/simpler`
  - strict startup sequence
  - directory ownership and task boundaries
  - local environment isolation for any install/test command
  - local known-issues tracking for defects found outside current scope
- `origin/htp/v0`
  - strict docs tree adapted for clean ICI: `docs/design`, `docs/todo`, `docs/in_progress`, `docs/story.md`, `docs/notes`
  - feature-sized task lifecycle
  - design docs start in `docs/in_progress/design/`, then merge into `docs/design/` before closeout

## Non-Goals For This First Setup PR

- Do not implement compiler, IR, runtime, backend, or examples yet.
- Do not import v0 code.
- Do not create `.codex/`, `.claude/`, or `.opencode/`.
- Do not vendor `.references/` or `.repositories/`; they remain ignored local reading inputs.
- Do not overfit the harness to AReaL, PyPTO, or Simpler domain specifics; extract durable process rules only.
- Do not add `docs/reference/` or `docs/research/`; all reading reports belong in `docs/notes/`.

## Target File Structure

Create this repository scaffold:

```text
AGENTS.md
README.md
.gitignore
.agents/
  README.md
  agents/
    compiler-architect.md
    docs-curator.md
    programming-surface-reviewer.md
    repo-reviewer.md
    verifier.md
  rules/
    agent-harness.md
    code-quality.md
    development-flow.md
    docs-and-knowledge.md
    evidence-and-verification.md
    security-and-environment.md
  skills/
    create-pr/SKILL.md
    design-first/SKILL.md
    implement-plan/SKILL.md
    review-pr/SKILL.md
    start-feature/SKILL.md
    verify-work/SKILL.md
  templates/
    design.md
    feature-task.md
    pr-body.md
    review-report.md
.github/
  pull_request_template.md
  workflows/policy.yml
scripts/
  check_repo_harness.py
tests/
  test_repo_harness.py
docs/
  README.md
  story.md
  design/README.md
  todo/README.md
  in_progress/README.md
  in_progress/repo_setup.md
  notes/README.md
  notes/agent_harness_sources.md
```

## Commit Sequence

### Commit 1: Record Setup Plan

**Files:**
- Create: `docs/in_progress/repo_setup.md`
- Keep: `.gitignore`

- [ ] **Step 1: Confirm branch and ignored references**

Run:

```bash
git status --short --branch
cat .gitignore
```

Expected:

```text
## htp/clean
?? .gitignore
```

`cat .gitignore` must include:

```text
.references/
.repositories/
```

- [ ] **Step 2: Commit the first planning state**

Run:

```bash
git add .gitignore docs/in_progress/repo_setup.md
git commit -m "docs: plan clean repo agent harness"
```

Expected:

```text
[htp/clean <sha>] docs: plan clean repo agent harness
```

### Commit 2: Add Root Docs And Task Lifecycle

**Files:**
- Create: `README.md`
- Create: `docs/README.md`
- Create: `docs/story.md`
- Create: `docs/design/README.md`
- Create: `docs/todo/README.md`
- Create: `docs/in_progress/README.md`
- Create: `docs/notes/README.md`
- Create: `docs/notes/agent_harness_sources.md`

- [ ] **Step 1: Create the docs skeleton**

Write `README.md` with:

```markdown
# ICI

ICI is being rebuilt from a clean branch as a human- and LLM-friendly intelligent compiler infrastructure.

The first project invariant is process quality: design, evidence, verification, and
agent workflow come before compiler implementation.

Start with:

- `AGENTS.md` for agent operating rules
- `docs/story.md` for the target framework story
- `docs/design/README.md` for implemented design
- `docs/todo/README.md` for open feature gaps
- `docs/in_progress/README.md` for active branch work
```

Write `docs/README.md` with:

```markdown
# ICI Documentation

This tree separates implemented design, future work, active work, and reading evidence.

- `docs/design/`: implemented behavior only
- `docs/todo/`: future or partial work only
- `docs/in_progress/`: active feature-branch tasks and design drafts
- `docs/story.md`: target framework story
- `docs/notes/`: document-reading and repository-reading reports
```

Write `docs/story.md` with:

```markdown
# ICI Story

ICI aims to be a compiler stack that is simultaneously human-friendly and
LLM-friendly.

The clean rebuild starts from one principle: every major compiler representation
must be explainable, inspectable, replayable, and verifiable before it becomes
an implementation dependency.
```

Write `docs/design/README.md` with:

```markdown
# Design

`docs/design/` contains implemented behavior only.

During a feature branch, draft designs live under `docs/in_progress/design/`.
Before the branch closes, validated design must be merged into the relevant
broad-topic files here, and stale in-progress drafts must be removed.

Implemented documents will be added as the clean system is built.
```

Write `docs/todo/README.md` with:

```markdown
# TODO

`docs/todo/` tracks feature-sized gaps that are not implemented yet.

## Current Gaps

- [ ] Agent harness scaffold
- [ ] Compiler story and architecture design
- [ ] Minimal package and verification tooling
- [ ] First executable compiler slice

Each future feature should have a clear input, output, and verification contract.
```

Write `docs/in_progress/README.md` with:

```markdown
# In-Progress Work

This directory tracks active feature branches.

Rules:

- one task file per feature-sized PR
- design-changing work must create `docs/in_progress/design/`
- completed design drafts must be merged into `docs/design/`
- stale task and design files must be removed before merge

## Active Tasks

- `docs/in_progress/repo_setup.md`
```

Write `docs/notes/README.md` with:

```markdown
# Notes

`docs/notes/` holds document-reading and repository-reading reports.

Local research clones and PDFs stay in ignored `.repositories/` and `.references/`.
When an agent reads them, it must write a concise report here with:

- source path or URL
- date read
- purpose of the reading
- extracted lessons
- decisions or rules affected

Notes are not normative until promoted into `docs/design/`, `docs/todo/`, or `.agents/rules/`.
```

Write `docs/notes/agent_harness_sources.md` with:

```markdown
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
- Preserve the v0 docs lifecycle: active drafts in `docs/in_progress/`, implemented design in `docs/design/`, and open gaps in `docs/todo/`.

## Decisions Affected

- Use `.agents/` as the only repo-local agent harness directory.
- Use `docs/notes/` for all document and repository reading reports.
- Ban `.codex/`, `.claude/`, and `.opencode/` from the clean branch scaffold.
- Add policy checks for harness shape and stale in-progress design drafts.
```

- [ ] **Step 2: Verify docs skeleton**

Run:

```bash
find docs -maxdepth 2 -type f | sort
```

Expected files include every path listed in this commit.

- [ ] **Step 3: Commit docs skeleton**

Run:

```bash
git add README.md docs
git commit -m "docs: add clean repository documentation skeleton"
```

### Commit 3: Add Agent Harness Entry And Rules

**Files:**
- Create: `AGENTS.md`
- Create: `.agents/README.md`
- Create: `.agents/rules/agent-harness.md`
- Create: `.agents/rules/code-quality.md`
- Create: `.agents/rules/development-flow.md`
- Create: `.agents/rules/docs-and-knowledge.md`
- Create: `.agents/rules/evidence-and-verification.md`
- Create: `.agents/rules/security-and-environment.md`

- [ ] **Step 1: Write `AGENTS.md` as a concise router**

Required contents:

```markdown
# ICI Agent Guide

This file is the Codex entrypoint for the clean ICI branch.

## Read First

Before editing, agents must:

1. run `git status --short --branch`
2. read `.agents/README.md`
3. read all files under `.agents/rules/`
4. load any task-relevant skill under `.agents/skills/<name>/SKILL.md`
5. inspect relevant docs under `docs/design/`, `docs/todo/`, and `docs/in_progress/`

## Harness Layout

- `.agents/rules/`: persistent project rules
- `.agents/skills/`: executable workflows
- `.agents/agents/`: expert consultation profiles
- `.agents/templates/`: reusable task, design, PR, and review templates

Do not create or depend on `.codex/`, `.claude/`, or `.opencode/` in this clean branch.
```

- [ ] **Step 2: Write `.agents/README.md`**

Required sections:

```markdown
# ICI Agent Harness

The harness is intentionally repo-local and Codex-readable through `AGENTS.md`.

## Principles

- keep root instructions short
- route detailed guidance into rules, skills, agents, and docs
- require evidence before completion claims
- prefer small plans with explicit verification over broad implementation prompts
- keep `.references/` and `.repositories/` ignored and local

## Layout

- `rules/`: mandatory project rules
- `skills/`: workflows agents can execute directly
- `agents/`: expert profiles for consultation
- `templates/`: standard document shapes
```

- [ ] **Step 3: Write rule files**

Each rule file must be concrete:

- `agent-harness.md`
  - no `.codex/`
  - root `AGENTS.md` is router only
  - `.agents/skills/` is workflow surface
  - expert profiles are read-only consultants unless user explicitly asks for delegation
- `development-flow.md`
  - feature-sized branches
  - task file first
  - design-first for architecture work
  - no stale `docs/in_progress/design/` before merge
  - no direct implementation without a written plan for multi-file work
- `docs-and-knowledge.md`
  - strict docs tree
  - document/repository readings must produce `docs/notes/` reports, not bulk-copied sources
  - local reading inputs remain ignored
  - design docs explain rationale, contracts, code pointers, and verification
- `evidence-and-verification.md`
  - every task has input, output, verification
  - minimal demos before complex debugging
  - no completion claims without fresh command output
  - PRs need tests or documented reason tests are impossible
- `code-quality.md`
  - typed, explicit, human-readable code
  - no stringly semantic ownership when typed structures are viable
  - no dict-shaped public APIs without a boundary reason
  - prefer composition and small modules
- `security-and-environment.md`
  - no secrets
  - no absolute user paths in committed docs
  - project-local virtual environments for install/test commands
  - ignored local reading clones are not committed

- [ ] **Step 4: Commit harness entry and rules**

Run:

```bash
git add AGENTS.md .agents/README.md .agents/rules
git commit -m "docs: add agent harness rules"
```

### Commit 4: Add Skills, Expert Profiles, And Templates

**Files:**
- Create: `.agents/skills/start-feature/SKILL.md`
- Create: `.agents/skills/design-first/SKILL.md`
- Create: `.agents/skills/implement-plan/SKILL.md`
- Create: `.agents/skills/verify-work/SKILL.md`
- Create: `.agents/skills/review-pr/SKILL.md`
- Create: `.agents/skills/create-pr/SKILL.md`
- Create: `.agents/agents/compiler-architect.md`
- Create: `.agents/agents/programming-surface-reviewer.md`
- Create: `.agents/agents/repo-reviewer.md`
- Create: `.agents/agents/docs-curator.md`
- Create: `.agents/agents/verifier.md`
- Create: `.agents/templates/design.md`
- Create: `.agents/templates/feature-task.md`
- Create: `.agents/templates/pr-body.md`
- Create: `.agents/templates/review-report.md`

- [ ] **Step 1: Add skills**

Skill responsibilities:

- `start-feature`
  - choose a gap from `docs/todo/README.md`
  - create `docs/in_progress/<feature>.md`
  - create `docs/in_progress/design/` for architectural work
  - make task/design files the first commit
- `design-first`
  - gather context
  - present alternatives
  - record decisions in `docs/in_progress/design/`
  - require acceptance criteria before implementation
- `implement-plan`
  - execute a written plan in small batches
  - run targeted verification after each batch
  - update the plan checklist as work lands
- `verify-work`
  - run the strongest available verification
  - capture exact commands and outputs
  - block completion claims without evidence
- `review-pr`
  - read-only review
  - classify risk by changed files and contracts
  - consult expert profile checklists
  - report findings by severity
- `create-pr`
  - verify clean branch state
  - require conventional, human-written commit message
  - prepare PR body using template
  - do not force-push without explicit approval

- [ ] **Step 2: Add expert profiles**

Profiles are markdown checklists, not runtime configuration:

- `compiler-architect.md`: compiler model, IR, pass, artifact, and replay consistency
- `programming-surface-reviewer.md`: human-native API and example readability
- `repo-reviewer.md`: branch policy, docs state, PR scope, and risk classification
- `docs-curator.md`: docs tree integrity and stale/duplicate prevention
- `verifier.md`: verification strategy, minimal demos, and command evidence

- [ ] **Step 3: Add templates**

Templates must define required headings:

- `design.md`: goal, alternatives, selected design, contracts, verification, closeout
- `feature-task.md`: branch, PR, scope checklist, docs plan, tests, closeout
- `pr-body.md`: Summary, Why, Contracts, Tests, CI, Scope, Reviewer Notes
- `review-report.md`: change analysis, findings, open questions, residual risk

- [ ] **Step 4: Commit skills and profiles**

Run:

```bash
git add .agents/skills .agents/agents .agents/templates
git commit -m "docs: add agent skills and expert profiles"
```

### Commit 5: Add Policy Checks And GitHub Workflow

**Files:**
- Create: `scripts/check_repo_harness.py`
- Create: `tests/test_repo_harness.py`
- Create: `.github/pull_request_template.md`
- Create: `.github/workflows/policy.yml`

- [ ] **Step 1: Add `scripts/check_repo_harness.py`**

The script must check:

- `AGENTS.md` exists
- `.agents/rules/`, `.agents/skills/`, `.agents/agents/`, `.agents/templates/` exist
- no `.codex/`, `.claude/`, or `.opencode/` directories exist
- docs root contains only approved top-level entries: `README.md`, `story.md`, `design`, `todo`, `in_progress`, `notes`
- `docs/notes/README.md` exists
- `docs/in_progress/design/*.md` is empty when `docs/in_progress/README.md` says no active tasks
- `.gitignore` ignores `.references/` and `.repositories/`
- `docs/reference/` and `docs/research/` do not exist

- [ ] **Step 2: Add `tests/test_repo_harness.py`**

Tests must import or subprocess the policy script and assert:

- clean scaffold passes
- prohibited harness directories fail
- stale in-progress design drafts fail when there are no active tasks

- [ ] **Step 3: Add GitHub PR template**

Use headings:

```markdown
## Summary

## Why

## Contracts

## Tests

## CI

## Scope

## Reviewer Notes
```

- [ ] **Step 4: Add GitHub policy workflow**

Use a minimal workflow:

```yaml
name: policy

on:
  pull_request:
  push:

jobs:
  repo-harness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python scripts/check_repo_harness.py
      - run: python -m unittest discover -s tests
```

- [ ] **Step 5: Commit policy checks**

Run:

```bash
git add scripts tests .github
git commit -m "ci: enforce clean repo harness policy"
```

### Commit 6: Close The Setup Task

**Files:**
- Modify: `docs/design/README.md`
- Create: `docs/design/agent_harness.md`
- Modify: `docs/todo/README.md`
- Modify: `docs/in_progress/README.md`
- Remove: `docs/in_progress/repo_setup.md`

- [ ] **Step 1: Promote implemented harness design**

Create `docs/design/agent_harness.md` with:

```markdown
# Agent Harness

This document describes the implemented clean-branch agent harness.

## Implemented Structure

- `AGENTS.md` is the Codex entrypoint and router.
- `.agents/rules/` holds mandatory project rules.
- `.agents/skills/` holds executable repo workflows.
- `.agents/agents/` holds expert consultation profiles.
- `.agents/templates/` holds reusable task, design, PR, and review templates.

## Rationale

The harness keeps root context short and stores durable project memory in small,
targeted files. It adopts AReaL's rules/skills/agents layering, PyPTO's
workflow discipline, Simpler's environment isolation, and v0's strict docs
lifecycle without bringing over legacy compiler implementation.

## Code Pointers

- `AGENTS.md`
- `.agents/README.md`
- `.agents/rules/`
- `.agents/skills/`
- `scripts/check_repo_harness.py`
```

Update `docs/design/README.md` to list `docs/design/agent_harness.md`.

- [ ] **Step 2: Update TODO and in-progress state**

In `docs/todo/README.md`, mark `Agent harness scaffold` complete and leave the
remaining clean-rebuild gaps open.

In `docs/in_progress/README.md`, replace the active task list with:

```markdown
## Active Tasks

None.
```

Remove `docs/in_progress/repo_setup.md`.

- [ ] **Step 3: Verify full scaffold**

Run:

```bash
python scripts/check_repo_harness.py
python -m unittest discover -s tests
```

Expected:

```text
repo harness policy passed
...
OK
```

- [ ] **Step 4: Commit closeout**

Run:

```bash
git add docs
git commit -m "docs: close agent harness setup"
```

## Acceptance Criteria

- `AGENTS.md` exists and routes Codex to `.agents/`.
- `.agents/` contains rules, skills, expert profiles, and templates.
- No `.codex/`, `.claude/`, or `.opencode/` directories exist.
- `.references/` and `.repositories/` remain ignored and uncommitted.
- `docs/notes/` exists and is the only committed place for document/repository reading reports.
- `docs/notes/agent_harness_sources.md` records the AReaL, PyPTO, Simpler, and v0 readings that shaped the harness.
- The docs lifecycle from v0 is present in clean form.
- The repo has a policy script and CI workflow that enforce the harness shape.
- The setup task is moved from `docs/in_progress/` into `docs/design/agent_harness.md` before closeout.
- Verification commands pass locally.

## Self-Review Checklist

- [x] The plan does not implement compiler code.
- [x] The plan uses `.agents/` and `AGENTS.md`, not `.codex/`.
- [x] Every planned file has an explicit role.
- [x] Every commit has verification or inspection steps.
- [x] Local reference inputs stay ignored and readings are captured under `docs/notes/`.
- [x] v0 docs lifecycle rules are preserved.
