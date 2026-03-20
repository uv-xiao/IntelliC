# AST-All-the-Way Redesign

## Purpose

This document defines the redesign target for PR `#67`. The feature is not a
narrow replay adjustment. It is a joint redesign of:

- programming surfaces,
- the IR system,
- the staged artifact model,
- and extension / island participation.

The primary project goal is now explicit: HTP must become a compiler stack that
is both human-friendly and LLM-friendly. The discipline that is supposed to
make that possible is AST all the way.

## Problem statement

The current repository proves a strong core architecture, but it still has an
important split:

- public programming surfaces are improving, but WSP/CSP still remain partly
  metadata-choreographic;
- staged artifacts are runnable Python, but the IR model still reads like
  “Python plus sidecar payloads” rather than one coherent Python-owned IR
  system;
- extension/MLIR participation returns usable artifacts, but the repo does not
  yet define a strong enough end-to-end contract for what a global HTP stage
  artifact must be.

That is the redesign target.

## Core decision

HTP should not model IR as a rigid stack of levels.

Instead, HTP should use:

- **one canonical carrier:** Python AST
- **many composable IR aspects:** typing, layout, effects, schedule, backend
  discharge facts, extension facts, and others
- **one execution rule:** every global stage artifact must remain renderable to
  native Python and executable through an interpreter/runtime path

This is a flattened IR system, not a tower of separate IR universes.

## Carrier-and-aspect model

### Carrier

The canonical carrier of every global HTP stage is Python AST.

That means:

- parsing produces Python AST
- passes mutate or replace Python AST
- extension islands may temporarily leave Python space, but must return a new
  Python-AST carrier before the next global stage boundary
- staged `program.py` is not only a convenience snapshot; it is the source
  rendering of the carrier

### Aspects

An HTP IR is then a composable bundle of aspects over the carrier.

Examples:

- type aspect
- layout aspect
- effect aspect
- schedule aspect
- backend discharge aspect
- extension-local aspect

An aspect should define:

- its schema / identity
- what Python-AST carrier it describes
- its dependencies on other aspects
- whether it contributes executable meaning or only analysis
- how it is validated against the carrier

This gives HTP a true composability protocol instead of a pile of unrelated
sidecars.

## Execution rule

The primary rule of the redesign is:

> Every global HTP stage artifact must be unparseable into native Python source
> and executable by an interpreter/runtime path.

This is the precise meaning of the new product goal.

### Human-friendly

Human-friendly means:

- the rendered stage artifact reads like native Python, not a compiler-only
  dump
- a human can inspect it, edit it, and understand the control/data structure
  without reconstructing opaque payload machinery

### LLM-friendly

LLM-friendly means:

- the rendered stage artifact is still executable
- a tool or agent can mechanically rewrite it and rerun it
- the runtime/interpreter path remains available after mutation

This is why “pretty source” alone is not enough. The artifact must still run.

## Programming surfaces and IR are one redesign

The redesign must treat programming surfaces and IR together.

Why:

- if frontend authoring is native Python but the first lowered artifact becomes
  ugly compiler data, the human-friendly goal is already broken
- if staged artifacts are readable but frontend/program transformations still
  revolve around metadata-heavy builder choreography, the LLM-friendly goal is
  still incomplete

So the new rule is:

- every new HTP IR family must define:
  - a programming surface
  - core carrier/aspect classes
  - an interpreter/runtime path
  - a rendering rule back to native Python source

## Pass model

A pass should do one or more of the following:

- mutate the Python-AST carrier
- add / update / remove aspects
- emit a locally temporary extension representation and then return to a Python
  carrier plus updated aspects

A pass contract therefore needs stronger declarations:

- carrier-preservation or carrier-rewrite policy
- aspect requirements
- aspect outputs / invalidations
- post-pass executability guarantee
- post-pass renderability guarantee

This is stricter than the current pass model and should drive the implementation
slice for this PR.

## Extension and MLIR rule

Extensions and MLIR pipelines are still allowed, but they must obey a stronger
boundary:

- they may operate on local representations internally
- they may emit their own evidence sidecars
- but before the next global HTP stage boundary, they must return:
  - a Python-AST carrier
  - valid aspect bundles for that carrier
  - an executable/renderable stage artifact

So MLIR is not forbidden. It is constrained to remain subordinate to the
Python-owned stage discipline.

## First implementation slice for this PR

PR `#67` should not attempt the whole redesign at once. The first slice should
do these things:

1. formalize the carrier/aspect/pass/extension contracts in code and docs
2. update programming-surface docs and TODOs so WSP/CSP work is explicitly part
   of the same redesign
3. make staged-artifact obligations explicit in the pass/artifact model
4. add tests that prove non-trivial rewritten stages still render to readable
   native Python and still execute

## Affected design docs

Before merge, the validated redesign must be reflected into:

- `docs/design/compiler_model.md`
- `docs/design/programming_surfaces.md`
- `docs/design/artifacts_replay_debug.md`
- `docs/design/pipeline_and_solver.md` if pass contracts change materially

## Success criteria

This redesign slice is successful when:

- the repo has a clear definition of a global HTP stage artifact
- that definition is carrier-based, aspect-based, and executable
- the programming-surface TODOs are explicitly part of the same redesign
- and the docs no longer describe the compiler model as effectively “closed”
  without the stronger AST-all-the-way guarantee being addressed
