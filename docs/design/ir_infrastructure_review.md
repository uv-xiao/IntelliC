# IR Infrastructure Review

This document reviews the current HTP IR infrastructure as the starting point
for the next product-gap PR. The purpose is not only to describe the code. It
is to identify the specific infrastructure decisions that still prevent WSP,
CSP, and staged artifacts from reading like native Python programs.

## Why this review exists

The AST-all-the-way redesign landed the main substrate:

- `ProgramModule` is the committed-stage semantic owner
- staged artifacts are Python-owned and runnable
- frontend ingress is registry-backed
- WSP/CSP have AST-backed nested-function capture

That is necessary, but it is not enough. Current flagship examples still expose
too much builder ceremony and too much metadata choreography. The remaining
problem is therefore not only “write prettier examples”. It is “find the IR
infrastructure decisions that force those examples to stay metadata-shaped”.

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
document is not the end state. It is the explicit problem statement for the IR
refinement, surface redesign, and example rewrite work that follows in this PR.
