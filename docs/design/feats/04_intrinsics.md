# Feature: Intrinsics (typed primitives with backend handlers)

## Goal

Expose low-level operations (vector ops, async copies, barriers, accelerators) in a way that is:

- **portable when possible** (multiple backends can implement the same contract),
- **explicitly target-specific when needed** (namespaced ops like `pto.*`),
- and **checkable** (layout/effects/capabilities, not “attrs as APIs”).

Intrinsics are the *only* way a kernel touches target-specific semantics. They are therefore a primary retargetability
surface.

---

## 1) Intrinsic contract: `IntrinsicDecl`

An intrinsic is declared by a contract object (conceptual schema):

- identity:
  - `name`: stable symbol name (e.g. `portable.add`, `portable.dot`, `pto.tma_async_copy`, `aie.mma`)
  - `version`: semantic version of the contract
- type signature:
  - `params`: list of typed parameters (`Tile[...]`, `Tensor[...]`, `Buffer[..., space]`, scalars, tokens)
  - `returns`: list of typed returns
  - `type_params`: explicit polymorphism (dtype/shape generics); no “duck typing”
- legality constraints:
  - `requires_layout`: facet predicates (distribution/memory/hardware facets)
  - `requires_caps`: capability tags (e.g. `cap.hw.async_copy.tma`, `cap.vec.width>=16`)
  - `requires_schedule`: scheduling predicates (alignment, pipeline stages, vector width constraints)
- effect interface:
  - `requires_effects`: obligations that must already hold
  - `produces_effects`: obligations introduced by the intrinsic (e.g. an async token)
  - `discharges_effects`: obligations that the intrinsic resolves (e.g. a `wait(token)` discharges `AsyncCopy(token)`)
- semantics:
  - minimal semantic spec sufficient for simulation and verification (not prose-only)
- diagnostics:
  - stable error codes + structured payload schema for violations

### 1.1 “Two-tier” intrinsic sets

HTP supports two classes, with the same contract mechanism:

1) **Portable intrinsics** (`portable.*`): multiple backends may implement the same semantics, possibly via different
   lowering strategies.
2) **Backend intrinsics** (`pto.*`, `aie.*`): explicitly constrain pipeline selection to targets that provide handlers.

This is the primary portability strategy: authors choose the portability tier explicitly, and the solver enforces it.

---

## 2) Handler interface (backend-provided)

Backends implement intrinsics via handlers. Split handlers into three roles so pipelines can be explicit about what they
need:

- `LoweringRule`: typed AST call → backend-ready structured op(s)
- `Emitter`: backend-ready op(s) → files/sections under `codegen/<backend>/...`
- `Simulator`: defines semantics for `RunnablePy` simulation mode

Not all pipelines require all roles, but HTP’s design constraint (“stages always runnable in `mode="sim"`”) implies:

- any intrinsic that can be executed by a stage program in sim must have either:
  - a `Simulator` handler, or
  - an explicit stub behavior that raises a structured diagnostic at runtime (still importable/executable).

In other words: “simulation semantics” is part of the intrinsic contract surface, not a bolt-on convenience.

### 2.1 Handler registration contract

A backend provides a registry mapping:

- `IntrinsicDecl.name@version` → handler set (`lower`, `emit`, `simulate` or explicit stub policy)

Missing handlers are not “runtime errors”; they are **capability mismatches** detected during pipeline selection and
reported as structured diagnostics.

---

## 3) Effects and async intrinsics (example contracts)

### 3.1 Async copy

`pto.tma_async_copy(src: Buffer[..., global], dst: Buffer[..., ub], bytes: i32) -> Token[AsyncCopy]`

- requires:
  - `requires_caps`: `cap.hw.async_copy.tma`
  - `requires_layout`: `dst.hw.space == "ub"`
- produces:
  - `produces_effects`: `AsyncCopy(token, src_space="global", dst_space="ub", bytes, ordering="relaxed")`

`portable.wait(token: Token[AsyncCopy]) -> ()`

- discharges:
  - `discharges_effects`: `AsyncCopy(token, ...)`

This makes ordering obligations explicit and checkable.

### 3.2 Barrier

`portable.barrier(scope: BarrierScope) -> ()`

- requires:
  - backend must support the selected `scope` (`cap.hw.barrier.scope=warp|block|tile|...`)
- produces/discharges:
  - may discharge pending async visibility obligations depending on the backend’s memory model

---

## 4) What this buys us (retargetability + extensibility)

- Intrinsics define the **semantic boundary** between portable kernels and backend specifics.
- Layout/effects/capabilities make legality checkable without relying on pass ordering folklore.
- Adding a backend becomes: declare capability support + implement handler tables, rather than forking pipelines.
