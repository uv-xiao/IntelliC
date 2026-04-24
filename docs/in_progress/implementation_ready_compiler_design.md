# Feature Task: Implementation-Ready Compiler Design

- Branch: `design/implementation-ready-compiler`
- PR: #70
- Owner: Codex
- Status: Active

## Goal

Make the accepted IntelliC compiler architecture implementation-ready before
the first executable compiler slice starts.

The current design explains the selected architecture. This PR should refine it
so an implementation agent can answer:

- what modules and files to create first
- which contracts each module owns
- what object identities, mutation paths, and database records are allowed
- what failure modes must be tested
- which examples prove the implementation behavior
- what is deliberately deferred

## Scope Checklist

- [x] Define input, output, and verification criteria
- [x] Write or update design docs if architecture changes
- [x] Clarify implementation order across syntax, semantics, actions, and surfaces
- [x] Clarify first-slice module contracts and ownership
- [x] Map design examples to concrete tests or evidence artifacts
- [x] Replace easy examples with challenging examples that prove nested regions,
  loop-carried values, TraceDB semantics, and actions work together
- [x] Review and make full SCF plus affine dialect support concrete enough for
  implementation
- [x] Verify locally
- [x] Sync `docs/design/`, `docs/todo/`, and `docs/in_progress/`

## Input

- Accepted compiler design:
  - `docs/design/compiler_framework.md`
  - `docs/design/compiler_syntax.md`
  - `docs/design/compiler_semantics.md`
  - `docs/design/compiler_passes.md`
- Source-reading evidence in `docs/notes/compiler_framework_sources.md`
- User instruction recorded in
  `docs/in_progress/human_words/compiler-framework.md`

## Output

- Updated accepted design docs with implementation-ready details.
- A focused in-progress design draft at
  `docs/in_progress/design/implementation_ready_compiler_design.md` while the
  PR is active.
- Clear verification mapping for the next implementation PR.

## Verification Criteria

- Every first-slice module group has an owner, public contract, dependencies,
  invariants, and failure modes.
- Each design example names an automated test or explicit evidence artifact.
- The design states a build order for syntax, TraceDB/semantics, actions, and
  surface construction APIs.
- The design separates first-slice work from deferred work.
- Documentation-only verification records exact checks run before handoff.

## Tests

Documentation-only task. Use:

```bash
python scripts/check_repo_harness.py
python -m unittest tests/test_repo_harness.py
```

Also perform focused rereads of the changed design sections and path/link
checks for referenced docs.

Verification run:

- `python scripts/check_repo_harness.py` — passed
- `python -m unittest tests/test_repo_harness.py` — passed
- `rg -n "Implementation-Ready|First-slice invariants|First-slice failure tests|Build Order|First Implementation Slice" docs/design/compiler_*.md docs/in_progress/implementation_ready_compiler_design.md` — confirmed the new design sections are present
- `rg -n 'sum_to_n|loop-body|challenging|LoopIteration|ValueConcreteTuple|scf.for_' docs/design/compiler_*.md docs/in_progress/design/implementation_ready_compiler_design.md docs/in_progress/implementation_ready_compiler_design.md docs/in_progress/human_words/compiler-framework.md` — confirmed the challenging examples and evidence hooks are present
- `rg -n 'Full SCF|Affine Syntax Coverage|Affine Semantics|SCF And Affine|affine_tile|AffineTransformLegality|scf.forall|affine.dma|Require affine' docs/design docs/in_progress docs/notes/compiler_framework_sources.md` — confirmed full SCF and affine design coverage is present

## Docs

- Add and refine `docs/in_progress/design/implementation_ready_compiler_design.md`.
- Promote the refined decisions into `docs/design/compiler_*.md` before closing
  the PR.
- Update `docs/todo/README.md` and this task file during closeout.

## Closeout

Before merge, move any accepted design changes into `docs/design/`, update
`docs/todo/README.md`, remove stale in-progress design drafts, and archive this
PR's `docs/in_progress/human_words/` under `docs/archive/`.
