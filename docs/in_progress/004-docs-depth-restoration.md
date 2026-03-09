# Docs Depth Restoration

- ID: `004-docs-depth-restoration`
- Branch: `htp/feat-docs-depth-restoration`
- PR: `TBD`
- Status: `in_review`
- Owner: `Codex`

## Goal

Restore the depth and usefulness of the documentation after the layered rewrite by turning the new layer files into detailed design and TODO documents. The implemented design docs must include rationale, feature explanation, and coding pointers grounded in the current codebase; the TODO docs must become detailed task checklists with useful completion accounting rather than coarse summaries.

## Why

- contract gap: the current layered docs have the right shape but are too brief to guide real implementation work
- user-facing impact: readers cannot recover the rationale and detailed guidance that existed before the structural rewrite
- architectural reason: a layered docs architecture is only useful if each layer is rich enough to drive design and implementation decisions

## Scope Checklist

- [x] recover detailed content from old docs and current code
- [x] expand `docs/design/layers/*.md` into detailed, code-backed layer docs
- [x] add feature listings, rationale, and coding pointers to implemented layer docs
- [x] expand `docs/todo/layers/*.md` into detailed task checklists per layer
- [x] add quantitative completion reporting to `docs/todo/README.md`
- [x] keep `docs/story.md` aligned with the deeper docs
- [x] verify tree shape, references, and policy alignment

## Code Surfaces

- producer: `docs/`, `README.md`, `AGENTS.md` if needed
- validator/binding: docs-policy automation only if path semantics change
- tests: docs layout tests and any policy tests affected by the richer docs model
- docs: implemented and TODO layer docs

## Test and Verification Plan

Required:
- [x] one happy-path policy/layout test if automation changes
- [x] one malformed-input / contract-violation test if automation changes
- [x] one regression test for doc-layout expectations if needed
- [x] human-readable docs structure verified
- [x] `pixi run verify` or documented fallback

## Documentation Plan

- [x] update `docs/design/` layer docs with detailed rationale, feature listings, and coding pointers
- [x] update `docs/todo/` layer docs with detailed task checklists and completion accounting
- [x] update `docs/story.md` if the deeper layering requires narrative alignment
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. recover old detail from git history and code
3. expand design layers
4. expand todo layers and README statistics
5. verify, rebase, review, and merge

## Review Notes

Reviewers should check both substance and structure: the layer docs must stay cleanly layered while becoming detailed enough to be implementation guides.
