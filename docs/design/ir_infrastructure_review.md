# IR Infrastructure Review

This document has two jobs.

First, it is a source-of-truth description of HTP's current IR and compiler
infrastructure: what the major objects are, how they relate, why the design
exists, and what is novel about it. Second, it is the review document for the
current PR scope: it identifies the specific infrastructure limits that still
block more native-Python WSP/CSP authoring and more readable staged artifacts.

It should be readable in two ways:

- by a beginner who wants to understand what HTP's compiler stack is trying to
  do and why it matters
- by a contributor who needs concrete fix targets for the remaining
  programming-surface work

## Why this document exists

HTP is not trying to be only another payload-to-backend translator. Its stated
goal is stricter:

- human-friendly compiler artifacts
- LLM-friendly compiler artifacts
- AST all the way

That goal forces the IR/compiler infrastructure to carry more responsibility
than a traditional hidden internal compiler IR. It is not enough for the
compiler to be correct internally. The intermediate forms must also be visible,
readable, runnable, and editable in Python space.

The AST-all-the-way redesign landed the main substrate:

- `ProgramModule` is the committed-stage semantic owner
- staged artifacts are Python-owned and runnable
- frontend ingress is registry-backed
- WSP/CSP have AST-backed nested-function capture

That is necessary, but it is not enough. Current flagship examples still expose
too much builder ceremony and too much metadata choreography. The remaining
problem is therefore not only “write prettier examples”. It is “find the IR
infrastructure decisions that force those examples to stay metadata-shaped”.

## HTP compiler stack in one picture

```text
human-authored Python
        |
        v
frontend capture
        |
        v
typed ProgramModule
  - items
  - aspects
  - analyses
  - identity
        |
        +--> passes transform or enrich ProgramModule
        |
        +--> interpreters run ProgramModule
        |
        `--> renderer emits normalized Python + stage state
```

The key point is that HTP tries to keep one shared semantic owner at committed
stage boundaries. Frontends, passes, interpreters, and artifacts all meet at
`ProgramModule`.

## Review scope

This review is focused on the path that currently blocks more native-Python
authoring:

- `htp/ir/core/`
- `htp/ir/program/`
- `htp/ir/frontends/`
- `htp/ir/dialects/wsp/`
- `htp/ir/dialects/csp/`
- interpreter and pass boundaries that constrain authored/staged readability

This review deliberately excludes backend-depth questions. Those remain tracked
under `docs/todo/alignment_and_product_gaps.md`.

## Core design idea

HTP's most important infrastructure decision is this:

- the compiler should have one Python-owned semantic owner at committed stage
  boundaries
- frontends should lower into that owner
- passes should transform that owner
- interpreters should execute that owner
- staged artifacts should reconstruct that owner

That decision is the reason HTP can claim all of the following at once:

- staged artifacts are not just debug dumps
- replay is not a separate auxiliary tool
- public surfaces and intermediate forms can stay close to each other
- extension participation does not automatically become semantic ownership

Without that decision, the project goal would collapse back into “nice
documentation around hidden internal compiler state”.

## Main infrastructure components

### `htp/ir/core/`

`htp/ir/core/` holds the shared substrate.

It contains the types of things the compiler needs regardless of which frontend
or dialect produced them:

- ids and identity records
- typed node models
- semantic summaries such as `KernelIR` and `WorkloadIR`
- aspect records for type/layout/effect/schedule
- analysis records

This is the part of the system that answers: “what are the common semantic
shapes HTP understands no matter where they came from?”

### `htp/ir/program/`

`htp/ir/program/` owns the committed-stage program container:

- `ProgramModule`
- program components
- rendering
- serialization
- composition helpers

This is where HTP says: “here is the whole current program state, in a typed
Python-owned form, ready for passes, interpretation, and staging”.

### `htp/ir/frontends/`

`htp/ir/frontends/` is the shared frontend-definition substrate.

It owns:

- frontend registration
- frontend rules
- AST capture context
- AST handler registration
- shared AST-lowering helpers
- shared `ProgramModule` assembly helpers

This is where HTP says: “different authored surfaces are allowed, but they must
enter the compiler through one coherent frontend mechanism”.

### `htp/ir/dialects/`

Dialects are where feature-specific frontend and local semantic behavior lives.

For the current review scope, the important dialects are:

- `htp/ir/dialects/wsp/`
- `htp/ir/dialects/csp/`

The design intent is:

- shared substrate in `core/`, `program/`, `frontends/`, `interpreters/`
- dialect-specific local meaning in `dialects/<name>/`

This is important because HTP should support dialect-specific syntax and local
meaning without letting dialects become private compiler universes.

### `htp/ir/interpreters/`

`htp/ir/interpreters/` is the execution side of the contract.

It proves that staged artifacts and typed IR are not only serializable; they are
also runnable. That matters for both:

- human debugging
- LLM/tool replay

The key design point is that interpretation is object-oriented and shared, not
one monolithic giant switch.

### `htp/passes/`

Passes operate on the shared program owner and are responsible for preserving
the stage boundary contract:

- valid typed state
- renderable staged Python
- replayable execution

This is where the compiler becomes more than a parser and renderer.

## Why this design is important

For a beginner, the novelty of HTP is not any single node type or surface
syntax. The novelty is the combination of these properties:

1. authored Python and intermediate Python are both first-class
2. committed-stage semantic ownership stays in Python space
3. replay is part of the compiler contract, not an afterthought
4. extensions/dialects can participate without taking semantic ownership away

Many compiler stacks can give you:

- an internal IR
- a frontend
- a backend

HTP is trying to give you something stricter:

- a compiler whose visible intermediate forms remain part of the product
  surface

That is why the IR infrastructure matters so much. If the IR shape is wrong,
every public surface will drift back toward encoded metadata.

## Worked example: how one program flows through HTP

At a high level, a program such as a tiled GEMM or process pipeline should flow
like this:

```text
authored Python
  -> frontend capture
  -> ProgramModule
  -> pass refinement
  -> staged normalized Python
  -> replay / interpretation
```

The same semantic owner should remain visible through that flow.

For example:

- WSP task-local structure should become real typed structure inside
  `ProgramModule`
- CSP process-local structure should become real typed structure inside
  `ProgramModule`
- staged Python should still read like the authored local structure, only in a
  normalized form

This is the point of AST all the way. It is not “use Python AST somewhere”.
It is “make the compiler's public intermediate forms remain Python-owned,
structured, and runnable throughout the flow”.

## What is already solid

The current infrastructure already proves several important points:

- one shared semantic owner exists at committed-stage boundaries
- WSP and CSP do not create private compiler pipelines
- staged `program.py` remains runnable through `ProgramModule.run(...)`
- dialect participation is explicit rather than import-order magic
- the interpreter stack is object-oriented rather than one monolithic executor

That means the current barriers are now narrower. The main failures are not
about missing global compiler ownership. They are about how local structure is
represented and therefore how local authored syntax can be expressed.

## Review findings

### 1. WSP stage structure is still metadata-owned

Current WSP authoring lowers task-local stage bodies into:

- `WSPTaskSpec.attrs["stages"]`
- `WSPTaskSpec.attrs["schedule"]`
- step objects whose primary identity is still a symbolic operation name

This is better than raw dict payloads, but it still keeps the real local
structure inside generic attr containers. That has three consequences:

- authored syntax still tends to look like schedule annotation rather than local
  program structure
- staged variants still read more like encoded plans than direct task-local code
- passes that want to manipulate stage-local behavior have to decode attrs
  instead of traversing first-class local structure

### 2. CSP process bodies are still partially metadata choreography

Current CSP authoring improved, but the dominant shape is still:

- process-local `compute(...)` / `compute_step(...)`
- explicit channel operations as named action markers
- process steps owned by flat step records rather than richer local process-body
  structure

This keeps CSP readable enough for a proof example, but not yet at the
human-first bar implied by `docs/story.md`. The user still writes a sequence of
operation markers, not a strongly native process body with clearer local data
and protocol intent.

### 3. Frontend capture is shared, but local lowering is still too ad hoc

The shared AST frontend substrate now exists and is the correct direction.
However, the WSP/CSP dialect frontends still need dialect-specific local
decoding and manual assembly around stage/process structure.

This is a real improvement over the previous state, but it still leaves:

- dialect-specific local lowering that is more manual than the final target
- a weak separation between “capture syntax” and “construct first-class local IR
  structure”
- too much dependence on local attr assembly in the final lowering step

### 4. The typed IR is strongest at top-level ownership, weaker in local bodies

The current IR is strongest at:

- `ProgramModule`
- `KernelIR`
- `WorkloadIR`
- typed identity/aspect records
- typed task/process graph nodes

It is weaker at:

- WSP stage-local structure
- CSP process-local structure
- local executable forms that should read as native code after rewriting

That mismatch explains the user-facing barrier: top-level ownership is clean,
but local authoring still falls back to metadata containers.

### 5. Example composition is fixed, but example authoring is still too ceremonial

`examples/ast_frontend_composability/demo.py` no longer performs manual
`ProgramItems` surgery, which was the previous blocker. That fix matters.

But the authored examples still reveal the current substrate limit:

- WSP example code still reads like a scheduled plan made of named steps
- CSP example code still reads like a protocol script made of action markers
- flagship examples still do not yet read like the best “native Python first”
  references

This means the remaining work must change both:

- IR representation
- public authoring shape

Changing only examples would be cosmetic.

## Design constraints raised by the review

The next implementation steps must satisfy these constraints.

### Constraint 1: local stage/process structure must become first-class

WSP stage-local and CSP process-local structure must no longer be primarily
owned by generic attrs. They need a more direct typed representation so:

- passes can transform them structurally
- interpreters can execute them structurally
- staged artifacts can render them structurally

### Constraint 2: authoring must target that first-class local structure directly

The public surfaces should not first construct metadata choreography that later
pretends to be local code. Authoring should lower directly into the refined
local IR structure.

### Constraint 3: staged variants must read like native local code, not encoded plans

The acceptance bar is not only “runnable” and not only “typed”. Staged variants
must be readable as local task/process code, which means the IR needs a shape
that can render that way without losing semantic ownership.

### Constraint 4: shared substrate must stay shared

This PR must not solve the problem by splitting WSP and CSP into new private IR
universes. Fixes must preserve:

- one shared `ProgramModule`
- one shared frontend substrate
- one shared interpreter substrate
- explicit dialect composition through typed interfaces

## Fix targets for the current PR

This review feeds the rest of PR `#68`. The implementation work that follows
should:

1. refine WSP/CSP local IR structure
2. rebuild WSP/CSP authoring on that refined local IR
3. rewrite flagship examples against the refined surfaces
4. verify that staged artifacts also become more native-Python readable

## Completion rule for this review

This review is only useful if the listed barriers are removed in code. The
document is not the end state. It is the explicit problem statement and current
source-of-truth architecture reference for the IR refinement, surface redesign,
and example rewrite work that follows in this PR.
