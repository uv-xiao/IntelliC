# ProgramModule IR Flow

This example is the human-facing proof surface for the current
AST-all-the-way redesign slice.

It demonstrates five things with explicit typed IR objects:

1. define a kernel-shaped IR program directly in Python
2. execute it through `ProgramModule.run(...)`
3. transform it into a rewritten IR program
4. define and execute a typed process-graph IR program
5. render the transformed module into staged `program.py` and rebuild it
6. prove a public surface can be resolved through a registered frontend rule

This example is intentionally small, but it is not a payload-dump test. The
point is to show how a person can author and inspect typed IR objects before
the full frontend/dialect substrate is finished.

Run it with:

`python -m examples.ir_program_module_flow.demo`
