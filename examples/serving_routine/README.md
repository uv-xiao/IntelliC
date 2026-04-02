# Serving Routine

This example demonstrates the current compiler-model surface for serving-style
programs.

What it proves:
- public types are structured and Python-native through `htp.types`
- routine tasks can carry first-class serving semantics such as `phase`,
  `state`, `stream`, and `batch`
- the resulting `state.json#/items/workload_ir` emits a routine summary instead
  of leaving serving structure hidden in example-local conventions

Run:

```bash
python -m examples.serving_routine.demo
```
