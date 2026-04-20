# AST Frontend Composability

This example validates the final frontend-definition slice of the AST-all-the-way
redesign.

It shows two human-first authored surfaces:

- a WSP program written with nested `@w.task(...)` / `@w.mainloop(...)`
  functions, local stage blocks, and operation calls such as `w.cp_async(...)`
- a CSP program written with nested `@c.process(...)` functions plus local
  bindings such as `packed = c.pack_tile(...)` and protocol calls such as
  `c.put(partials, packed)`

The demo lowers both through the AST-backed frontend substrate, composes the
resulting typed `ProgramModule`s into one shared module, and runs that composed
module through the shared object-oriented interpreter entry.
