# Design

`docs/design/` contains accepted architecture and implemented behavior only.

During a feature branch, draft designs live under `docs/in_progress/design/`.
Before the branch closes, validated design must be merged into the relevant
broad-topic files here, and stale in-progress drafts must be removed.

Accepted and implemented documents will be added as the clean system is built.

## Implemented Documents

- `docs/design/agent_harness.md` — clean-branch agent harness, rules, skills, profiles, templates, and policy checks.
- `docs/design/compiler_framework.md` — accepted high-level IntelliC compiler architecture and decomposition.
- `docs/design/compiler_syntax.md` — accepted syntax (`Sy`) design derived from MLIR/xDSL structure and canonical IR parsing.
- `docs/design/compiler_semantics.md` — accepted semantics (`Se`) design built around typed `SemanticDef` records and shared `TraceDB`.
- `docs/design/compiler_passes.md` — accepted compiler action, pipeline, and agent-participation design.
