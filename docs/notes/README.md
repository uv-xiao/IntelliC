# Notes

`docs/notes/` holds document-reading and repository-reading reports.

Local research clones and PDFs stay in ignored `.repositories/` and `.references/`.
When an agent reads them, it must write a concrete report here with enough
structure for a later human or LLM agent to reconstruct why the source mattered.
Notes must not be summary-only. They should preserve the useful shape of the
source reading, not just conclusions.

Every substantial note should include:

- source path or URL
- date read
- purpose of the reading
- source map or scope table
- visual model, diagram, or flowchart when the source describes structure,
  process, architecture, or data flow
- code, command, schema, or pseudocode sketches when the source affects APIs,
  implementation shape, verification, or examples
- extracted lessons tied to source evidence
- comparison or decision tables when multiple sources or approaches are weighed
- decisions or rules affected
- verification or follow-up evidence that should be created from the reading

Notes are not normative until promoted into `docs/design/`, `docs/todo/`, or `.agents/rules/`.

Useful forms include:

```text
ASCII diagrams for ownership or data flow
Mermaid flowcharts for process and lifecycle
Markdown tables for source comparison and decisions
Small code blocks for API sketches, command lines, schemas, and examples
Checklists for follow-up evidence
```

A short note is acceptable only when the source is small or rejected as
irrelevant. If the source informs a design, rule, or task, the note should carry
enough concrete detail to review the decision without reopening every original
source immediately.
