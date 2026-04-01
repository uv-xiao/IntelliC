# Module Organization and Code Quality Contract

This document defines the repository-wide module-organization and code-quality
rules for PR `#67`. It exists because the current branch has made the new IR
substrate real enough that file/module structure now matters for long-term
maintenance, not only local correctness.

## Why this refactor is mandatory

Current quality problems are structural, not cosmetic:

- `htp/kernel.py` owns public authoring, traced capture, payload assembly,
  IR/lowering glue, and helper logic in one large module.
- `htp/ir/program/module.py` mixes typed semantic ownership with payload/state
  serialization and compatibility rebuilding.
- `htp/ir/frontends/__init__.py` mixes registry concerns, builtin registrations, and
  surface-specific lowering logic.
- `htp/ir/interpreters/entrypoints.py` mixes execution environment, expression evaluation,
  statement execution, top-level interpreters, and report shaping.
- several public-surface and IR modules still let dict payloads and string refs
  leak into semantic ownership instead of confining them to explicit
  serialization boundaries.

If PR `#67` closes on top of that structure, the code will technically work but
remain hard to extend, review, and safely modify.

## Required module ownership model

HTP must be organized around explicit ownership, not convenience imports.

## Required `htp/ir/` package layout

The flat `htp/ir/` namespace is itself a defect. It mixes:

- core substrate files
- program-container files
- frontend infrastructure
- interpreter infrastructure
- dialect-specific node files

These must be split into subpackages.

Target layout:

- `htp/ir/program/`
  - `module.py`
  - `components.py`
  - `serialization.py`
  - `render.py`
  - `build.py`
- `htp/ir/core/`
  - `nodes.py`
  - `types.py`
  - `layout.py`
  - `ids.py`
  - `maps.py`
  - `aspects.py`
  - `analysis.py`
  - `identity.py`
  - `semantics.py`
  - `op_specs.py`
- `htp/ir/frontends/`
  - `registry.py`
  - `builtin.py`
  - `rules.py`
  - `shared.py`
  - `kernel.py`
- `htp/ir/interpreters/`
  - `registry.py`
  - `runtime.py`
  - `nodes.py`
  - `entrypoints.py`
- `htp/ir/dialects/`
  - `registry.py`
  - `wsp.py`
  - `csp.py`

This is not optional cleanup. It is part of the architecture contract.

### Why this layout

- `program/` isolates `ProgramModule` and staged-artifact ownership
- `core/` isolates the typed IR substrate from authoring/runtime details
- `frontends/` isolates lowering infrastructure from public-surface modules
- `interpreters/` isolates execution machinery from the rest of the IR package
- `dialects/` prevents framework-specific typed nodes from polluting the same
  namespace as core nodes

### 1. Public surface modules

Files such as:

- `htp/kernel.py`
- `htp/routine.py`
- `htp/wsp/__init__.py`
- `htp/csp/__init__.py`
- `htp/ark/__init__.py`

own only:

- human-facing authoring APIs
- public surface dataclasses/specs
- traced authoring entrypoints
- lightweight validation of user-facing arguments

They must not own:

- `ProgramModule` serialization details
- backend-specific lowering
- pass logic
- artifact layout logic
- global registry mutation beyond explicit registration hooks

### 2. IR substrate modules

Files under `htp/ir/core/`, `htp/ir/program/`, `htp/ir/frontends/`,
`htp/ir/interpreters/`, and `htp/ir/dialects/` own:

- typed semantic objects
- identities / bindings / scopes / maps
- aspects / analyses
- frontend lowering substrate
- dialect substrate
- interpreter substrate

They must not own:

- public-user decorator ergonomics
- backend build/load/run behavior
- package emission policy

### 3. Serialization modules

Payload, JSON, and replay/state serialization must be isolated. Typed semantic
ownership must not be implemented as ad hoc dict assembly scattered across
public surfaces and passes.

Serialization code may convert to/from mappings, but it must live in dedicated
serialization helpers, not in the semantic core by default.

### 4. Pass modules

Files under `htp/passes/` own:

- typed-object transformations
- analysis production/invalidation
- committed-stage construction

They must not become a second semantic owner through raw payload mutation.

### 5. Artifact modules

Files under `htp/artifacts/` own:

- package/stage emission
- manifest/state/stage file layout
- artifact validation helpers

They must not own frontend semantics or backend lowering policy.

## Mandatory code-quality rules

These are strict rules for all new architecture work on this branch.

### No semantic string refs

Semantic references must use typed ids or typed reference objects.

Allowed:

- readable names for display
- inert labels in docs/example text
- explicit serialization at boundaries

Not allowed:

- stringly-typed semantic linkage between nodes, scopes, channels, tasks, or
  bindings when a typed id/ref object is viable

### No dict-owned semantics

Typed Python objects are the semantic owner.

Allowed:

- payload dicts at serialization boundaries
- low-level malformed-artifact tests

Not allowed:

- new program-facing logic centered on `dict[str, Any]`
- nested semantic state encoded as ad hoc attrs payloads when a typed class can
  own the contract

### No monolithic multi-role modules

If a file owns more than one of the following, it should be split:

- public authoring
- typed semantics
- serialization
- registry/discovery
- interpreter execution
- pass logic
- artifact emission

Large files are not forbidden solely on line count, but they need a single
coherent responsibility. A large module that mixes multiple roles is a defect.

## Immediate refactor targets on this branch

Before continuing feature development, the branch must refactor the current
implementation to match this ownership model.

### A. ProgramModule split

`htp/ir/program/module.py` should stop owning every concern directly.

Target split:

- program-core objects
- payload/state conversion helpers
- view/rebuild helpers

The public import path may stay stable, but implementation concerns must be
factored internally.

### B. Frontend registry split

`htp/ir/frontends/` should separate:

- frontend registry
- builtin frontend registration
- workload/lowering adapters

Public-surface modules should delegate into that substrate instead of building
payloads locally.

### C. Interpreter split

`htp/ir/interpreters/` should separate:

- execution environment
- expression evaluation
- statement execution
- item interpreters
- execution report shaping

This is required to keep the OO interpreter design comprehensible and
extensible.

### D. Public surface cleanup

`htp/kernel.py`, `htp/routine.py`, `htp/wsp/__init__.py`, and `htp/csp/__init__.py`
should be treated as public façades. Lowering/building/serialization helpers
should migrate out of them whenever they are not purely public-surface logic.

## Refactor progress on this branch

Implemented now:

- the old flat modules have already been internally split by responsibility,
  but not yet fully moved into the target subpackage hierarchy
- `htp/ir/program/module.py` is reduced to the public `ProgramModule` façade, while
  program component ownership and payload/state conversion are split into:
  - `htp/ir/program_components.py`
  - `htp/ir/program_serialization.py`
- `htp/ir/frontends/__init__.py` is reduced to the public frontend API surface, while
  registry ownership and builtin-registration ownership are split into:
  - `htp/ir/frontend_registry.py`
  - `htp/ir/builtin_frontends.py`
- `htp/ir/interpreters/entrypoints.py` is reduced to the interpreter-registration façade,
  while runtime helpers and object-owned interpreter units are split into:
  - `htp/ir/node_runtime.py`
  - `htp/ir/node_interpreters.py`
- kernel-to-`ProgramModule` lowering is no longer owned directly by
  `htp/kernel.py`; it now lives in `htp/ir/frontends/kernel.py`

Still open:

- physical move from the flat namespace into the target subpackage hierarchy
- further public-surface façade cleanup for routine/WSP/CSP
- pass-side cleanup for the remaining large pass modules, especially where
  payload-oriented helper logic still sits beside typed-object pass behavior

## Merge bar for this refactor

PR `#67` must not close with the current “works but messy” structure.

At minimum before merge:

- core IR/program/frontend/interpreter code follows explicit ownership seams
- new architecture work no longer introduces stringly semantic refs
- new architecture work no longer introduces dict-owned semantic contracts
- the public-surface to IR path is more modular than the current state
- docs and agent rules explicitly encode these constraints
