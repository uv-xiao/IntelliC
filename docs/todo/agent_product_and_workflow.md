# TODO — Agent Product and Workflow

This document tracks the remaining gap between today’s disciplined workflow/tooling and the final agent-native framework product.

## Completion snapshot

- total checklist items: 8
- complete: 5
- partial: 2
- open: 1

## Detailed checklist

### Tooling surface
- [x] Provide replay, verify, semantic diff, explain, bisect, minimize, and promote-plan tools.
- [x] Keep diagnostics and fix-hint policies machine-consumable.
- [~] Broaden autonomous patch / verify / promote loops beyond the current tool surface.

### Repository workflow
- [x] Enforce `htp/dev` as stable and `htp/feat-*` for feature work.
- [x] Enforce `docs/in_progress/` task files as part of feature PR workflow.
- [x] Keep `docs/design/`, `docs/todo/`, and `docs/in_progress/` as explicit repository state surfaces.
- [~] Continue refining example/test/doc quality rules so human readability and agent reliability improve together.
- [ ] Build fuller agent-native development controls beyond the current workflow and policy scaffolding.

Recent progress in this area includes the public `htp.kernel` / `htp.routine`
surface, traced decorator-style flagship authoring, and the replacement of raw
top-level program blobs in flagship examples.
The remaining gap is stronger automation around those quality rules, not the
absence of any rule set at all.

## Why these tasks remain

This topic improved substantially with the docs/process work, but the full target still includes stronger autonomous loops and richer machine-guided development behavior than the repository currently provides.

## Coding pointers

Relevant anchors:
- `htp/agent_policy.py`
- `htp/tools.py`
- `htp/diagnostics.py`
- `AGENTS.md`
- `.agent/rules/`
- `.github/scripts/check_pr_policy.py`
