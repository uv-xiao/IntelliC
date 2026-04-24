# Human Words

This directory records human instructions captured during active work.

Use it for source-of-truth wording from the user that affects an in-progress
task, design, rule, or implementation direction. Preserve the user's wording as
closely as possible, along with date and context.

Human words are not normative by themselves. Promote curated decisions into
`.agents/rules/`, `docs/in_progress/`, `docs/todo/`, or `docs/design/` when
they become project rules, task scope, or implemented design.

When the active PR closes, move that PR's records into
`docs/archive/<pr-number-or-slug>-<pr-title-slug>/human_words/` and recreate
this README for the next active task.
