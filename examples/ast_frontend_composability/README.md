# AST Frontend Composability

This example validates the final frontend-definition slice of the AST-all-the-way
redesign.

It shows two human-first authored surfaces:

- a WSP program written with nested `@w.task(...)` / `@w.mainloop(...)`
  functions plus local `w.step(...)` calls
- a CSP program written with nested `@c.process(...)` functions plus local
  `c.get(...)`, `c.put(...)`, and `c.compute(...)` calls

The demo lowers both through the AST-backed frontend substrate, composes the
resulting typed `ProgramModule`s into one shared module, and runs that composed
module through the shared object-oriented interpreter entry.
