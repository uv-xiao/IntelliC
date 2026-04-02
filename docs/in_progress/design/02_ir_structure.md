# IR Structure

## Shared node substrate

HTP should use one shared typed node substrate.

Top-level item kinds:

- `Kernel`
- `Routine`
- `TaskGraph`
- `ProcessGraph`

They reuse one shared expression/statement core rather than separate semantic
universes.

## Common node hierarchy

The minimum common hierarchy should include:

- `Node`
- `Item`
- `Expr`
- `Stmt`
- `Region`
- `Aspect`
- `Analysis`

## Shared expression families

Core shared expressions should cover:

- literals / constants
- typed references
- arithmetic / logic
- comparison / predicates
- indexing / slicing / views
- typed intrinsic calls
- structured numeric ops such as reductions and abstract matmul

## Shared statement families

Core shared statements should cover:

- binding / assignment
- store / writeback
- allocation / storage introduction
- if / loop / while / region control
- launch / invoke / call-like dispatch
- send / receive / await / barrier / sync

## Identity and references

Stringly-typed semantic references are banned.

Semantic references must use typed ids and typed ref nodes.

Minimum ids:

- `NodeId`
- `ItemId`
- `SymbolId`
- `BindingId`
- `ScopeId`
- `RegionId`
- `TaskId`
- `ProcessId`
- `ChannelId`

Readable names may appear in emitted Python, but they are projections of
stable ids, not semantic truth.

This should also guide implementation style:

- avoid stringly-typed semantic wiring in new IR code
- avoid dict-shaped semantic programming when typed objects can own the state
- prefer object-oriented decomposition over monolithic procedural helpers when
  that makes ownership and invariants clearer

## Symbols, bindings, scopes, regions

HTP distinguishes:

- `Symbol`
  - logical entity
- `Binding`
  - scoped introduction of a symbol

Each scope defines:

- `scope_id`
- `parent_scope_id`
- introduced bindings
- scope kind

`Region` is first-class and owns:

- `region_id`
- `scope_id`
- ordered child statements/nodes
- region kind

Graph topology and lexical scope are distinct:

- lexical scope controls use resolution
- graph edges control task/process/channel topology

## Type and value split

HTP distinguishes:

- types
- values
- aspects

Dimensions and indices are first-class values, not only type parameters.

Storage is a typed storage object.

Views are value-level objects with:

- source storage/view reference
- explicit transform
- resulting view type

## Core vs extension semantic boundary

Builtin core concepts:

- dimensions
- indices
- storage
- views

Extension concepts:

- framework-specific axis systems such as Arknife axes

Axis systems compile down to core dimensions / indices / layout facts and
extension-owned aspects. They do not redefine the core substrate.
