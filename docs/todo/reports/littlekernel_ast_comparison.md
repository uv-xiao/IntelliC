# HTP vs LittleKernel AST-Centric Comparison

This report tracks the remaining comparison work between HTP's Python-AST-first
compiler and `references/triton-distributed-knowingnothing/python/little_kernel`.

## Why it remains

HTP now has code-backed programming surfaces that are materially closer to the
LittleKernel bar, but the repository still does not contain a full written
comparison of:

- how both systems use Python as the authoring medium
- where HTP keeps Python AST canonical while LittleKernel transitions into its
  own statement/expression substrate
- how replayable Python stages change debugging and agent-oriented compiler
  development
- what schedule/dataflow authoring patterns HTP should still learn from
  LittleKernel

## Remaining checklist

- [ ] compare canonical forms and lowering ownership
- [ ] compare schedule/dataflow authoring surfaces on concrete examples
- [ ] compare debugging / replay / intermediate evidence
- [ ] extract concrete next-step surface improvements for HTP

## Relevant references

- `references/triton-distributed-knowingnothing/python/little_kernel/language/`
- `references/triton-distributed-knowingnothing/python/little_kernel/design/sm90_bf16_gemm.py`
- `docs/story.md`
- `docs/design/02_programming_surfaces.md`
