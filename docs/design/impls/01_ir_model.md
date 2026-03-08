# Impl: IR Model (AST-first + typed metadata)

## Goal

Define the minimal internal representation strategy that preserves Python extensibility.

Current code anchors:

- `htp/ir/semantics.py`
- `htp/ir/types.py`
- `htp/ir/op_specs.py`
- `htp/passes/program_model.py`
- `htp/intrinsics.py`

This design deliberately exploits a Python-specific advantage: because the IR is Python AST, every intermediate stage can
also emit a **runnable Python program** (host/orchestration level) for replay, simulation, and debugging.

HTP strengthens this into a hard invariant:

> Every compilation stage must be runnable in `mode="sim"`.

This requirement is not “nice to have”; it directly constrains what the intermediate IR can be and how it can be
extended.

---

## 1) IR layers

1. **Source AST**: parsed Python AST of entrypoints.
2. **Canonical AST**: normalized AST for deterministic passes.
3. **Typed AST**: canonical AST + attached metadata:
   - symbol table + type info
   - layout facets
   - schedule directives
   - effect annotations
4. **Backend-ready forms**:
   - for PTO: codegen-ready kernel/task representation
   - for AIE: MLIR-AIE module(s) as backend artifacts under `codegen/aie/`

---

## 1.5) The executable-IR invariant (what “always runnable” implies)

“Always runnable in sim mode” indicates that HTP’s intermediate representation must remain an **executable language** at
all stages, not merely a data structure for compilers.

This implies:

1) **IR extensions must have executable semantics**, not just syntactic shape.
   - If we introduce a new internal node/kind, it must correspond to Python code that can execute in sim (typically via a
     runtime shim call), or it must lower immediately into such code in the same pass.
2) **Lowering is staged as “residual programs”**, not as a one-way lowering into opaque internal IR.
   - A “lowered” stage is still a Python program; it may carry extra metadata/attachments (analyses, island handles,
     backend-ready forms) but it cannot become non-executable.
3) **External toolchains and extension-owned IR islands are accelerators, not semantic owners**.
   - Whether HTP is emitting one-way artifacts for an external toolchain or round-tripping through an optional extension,
     it cannot delete the program’s sim semantics.
   - The stage must remain runnable by keeping (or reconstructing) a Python-level executable representation and routing
     accelerated regions through runtime shims (or explicit stubs) with defined sim behavior.

Practically, HTP must define an explicit “executable subset” of Python AST plus a small, stable runtime API that gives
semantics to IR-level operations.

---

## 2) Identity model (indexing Python constructs in a compiler)

HTP must not rely on Python object identity. Every Python construct that can be referenced by:

- diagnostics,
- analyses,
- or before/after mappings across passes

needs a stable indexing scheme.

HTP therefore uses multiple identity layers with different stability guarantees:

### 2.1 `node_id` (stage-local, deterministic)

Every AST node that can appear in diagnostics, dumps, or traces has a stage-local `node_id`.

Recommended scheme (deterministic within a stage):

- `def_id`: canonical symbol path of the owning definition (a.k.a. `symbol_path`, e.g. `module::add::add_tile`)
- `kind`: node kind tag (e.g. `Call`, `For`, `KernelDef`, `ChannelSend`)
- `ordinal`: deterministic pre-order index within the owning definition after canonicalization
- `span`: `(file, line, col)` when available (debug only; not a primary key)

`node_id = f"{def_id}:{kind}:{ordinal}"`

Design intent:

- `node_id` is stable enough for **within-stage** blame and for connecting `ir/pass_trace.jsonl` → dumps.
- `node_id` is *not* intended to persist across AST mutations (ordinals will shift).

### 2.2 `entity_id` (cross-stage, semantic identity)

Many analyses must talk about “the same construct” across transformations:

- “this loop is the k-loop we pipeline”
- “this buffer is the ping-pong allocation for A”
- “this channel is the l2c FIFO”

For this, we introduce a persistent `entity_id`.

Definition:

- `entity_id` is a stable identifier for a semantic object, intended to persist across passes when the pass preserves the
  object’s meaning.

Recommended representation:

- `entity_id = f"{def_id}:E{entity_ordinal}"`
- where `entity_ordinal` is assigned deterministically in capture/canonicalization order, and then **propagated** by
  rewriting passes.

Propagation rule (contract-level):

- When a pass rewrites a node but considers it the “same semantic object”, it must propagate the `entity_id`.
- When a pass creates a new semantic object, it assigns a new `entity_id` and records provenance (see mapping files below).

This is the key mechanism for before/after mappings that are meaningful for humans and agents.

#### 2.2.1 Stage artifact: `ids/entities.json` (normative v1 minimum schema)

Each stage must emit `ids/entities.json` to make identity machine-consumable:

```json
{
  "schema": "htp.ids.entities.v1",
  "def_id": "module::matmul_tile",
  "entities": [
    {"entity_id": "module::matmul_tile:E12", "kind": "For", "role": "loop_k"},
    {"entity_id": "module::matmul_tile:E40", "kind": "Call", "role": "mma"}
  ],
  "node_to_entity": [
    {"node_id": "module::matmul_tile:For:7", "entity_id": "module::matmul_tile:E12"},
    {"node_id": "module::matmul_tile:Call:31", "entity_id": "module::matmul_tile:E40"}
  ]
}
```

Notes:

- `entities[]` is a registry; `role` is optional but useful for downstream analyses.
- `node_to_entity[]` makes it easy to attach analysis anchors to stage dumps without heuristic matching.

### 2.3 `binding_id` (variable identity, resolves shadowing/renaming)

Names in Python are ambiguous across scopes and shadowing; analyses must not refer to variables by raw string name.

HTP therefore introduces a scoped binding identity:

- `binding_id`: identifies a *specific binding* (definition site) of a name.

Examples of binding sites:

- function/kernel parameters
- loop induction variables
- assignment targets in the HTP subset

Recommended representation:

- `scope_id = f"{def_id}:S{scope_ordinal}"` (lexical scope identity, deterministic)
- `binding_id = f"{scope_id}:B{binding_ordinal}"`

Then each `Name` occurrence in the AST is annotated in metadata with:

- `name_use.node_id` → `binding_id`

This lets analyses index “the variable” robustly even if later passes rename it for codegen or canonicalization.

#### 2.3.1 Stage artifact: `ids/bindings.json` (normative v1 minimum schema)

Each stage must emit `ids/bindings.json`:

```json
{
  "schema": "htp.ids.bindings.v1",
  "def_id": "module::matmul_tile",
  "scopes": [
    {"scope_id": "module::matmul_tile:S0", "parent": null, "kind": "function"},
    {"scope_id": "module::matmul_tile:S3", "parent": "module::matmul_tile:S0", "kind": "for"}
  ],
  "bindings": [
    {"binding_id": "module::matmul_tile:S3:B1", "name": "k", "site_entity_id": "module::matmul_tile:E12"}
  ],
  "name_uses": [
    {"node_id": "module::matmul_tile:Name:19", "binding_id": "module::matmul_tile:S3:B1"}
  ]
}
```

Notes:

- `site_entity_id` ties a binding definition to the construct that defines it (useful for rewrite mapping and legality).
- if a pass rewrites bindings (splits induction variables, outlines regions), it must emit `maps/binding_map.json`.

### 2.4 What analyses should reference

Rule of thumb:

- **Within-stage** analyses can reference `node_id` for precision.
- Any analysis meant to survive or be compared across stages should reference:
  - `entity_id` for statements/constructs, and
  - `binding_id` for variables.

This is how we avoid the common failure mode: “analysis mentions `k` but `k` was renamed/split and the plan is now wrong”.

### 2.5 Mapping files (before/after links across a mutating pass)

When a pass performs major rewrites, it should emit mapping/provenance files into the *after-stage* directory, e.g.:

- `ir/stages/<after>/maps/entity_map.json`
- `ir/stages/<after>/maps/binding_map.json` (when bindings are rewritten)

Normative minimum `entity_map.json` shape:

```json
{
  "schema": "htp.entity_map.v1",
  "pass_id": "pkg::pass@1",
  "stage_before": "s06",
  "stage_after": "s07",
  "entities": [
    {"before": "module::matmul:E12", "after": ["module::matmul:E12"], "reason": "preserved"},
    {"before": "module::matmul:E33", "after": ["module::matmul:E41", "module::matmul:E42"], "reason": "split_unrolled"},
    {"before": null, "after": ["module::matmul:E88"], "reason": "introduced_pingpong_buffer", "origin": ["module::matmul:E12"]}
  ]
}
```

Design intent:

- mappings are explicit evidence for stage diffs and autonomous debugging,
- and they avoid heuristic structural matching of AST dumps.

Normative minimum `binding_map.json` shape:

```json
{
  "schema": "htp.binding_map.v1",
  "pass_id": "pkg::pass@1",
  "stage_before": "s06",
  "stage_after": "s07",
  "bindings": [
    {
      "before": "module::matmul:S3:B1",
      "after": ["module::matmul:S3:B1"],
      "reason": "preserved"
    },
    {
      "before": "module::matmul:S3:B2",
      "after": ["module::matmul:S5:B1", "module::matmul:S5:B2"],
      "reason": "split_unrolled"
    },
    {
      "before": null,
      "after": ["module::matmul:S7:B4"],
      "reason": "introduced_temp",
      "origin": ["module::matmul:E88"]
    }
  ]
}
```

---

## 3) Metadata attachment model

Typed metadata is stored separately from the AST structure and keyed by `node_id` and symbol paths:

- `types`: inferred types (tile/tensor/buffer/scalars)
- `layout`: facet product values (distribution/memory/hardware)
- `effects`: protocol obligations (channels, async tokens, barriers, collectives)
- `schedule`: schedule directives and their resolved/unsatisfied constraints

In addition, identity registries are staged to support cross-stage analyses and mappings:

- `ids/entities.json` for `entity_id` assignment and node_id → entity_id association
- `ids/bindings.json` for `binding_id` registries and Name-use → binding_id association

Metadata must be:

- serializable (JSON-compatible),
- deterministic (stable ordering),
- and derivable from the canonical AST plus extension-provided analyses (no hidden state).

---

## 4) Analysis results (first-class, staged)

A key architectural requirement is to distinguish:

- **transformations** that produce a new AST (new runnable replay stage), from
- **analyses** that produce typed data structures used by later passes and humans/agents.

Analyses are not “compiler-internal whispers”: if an analysis justifies a rewrite or a legality decision, it must be
serializable and included in the artifact package.

### 4.1 Analysis identity (minimum)

Each analysis result is keyed by:

- `analysis_id`: `pkg::name@version`
- `schema`: `htp.analysis.<name>.vN` (schema identifier)

### 4.2 Where analyses live

Analyses belong to a stage and are emitted under:

- `ir/stages/<stage_id>/analysis/`
  - `index.json`
  - one file per analysis result

See pass manager details: `docs/design/impls/02_pass_manager.md`.

---

## 5) Dump schema and replay program (`RunnablePy`)

Each stage emits:

- `program.pyast.json`: the canonical AST dump (structural)
- `program.py`: a **generated runnable Python** file that replays the stage
- `env.json`: captured compile-time constants and configuration bindings needed for replay

### 4.1 What “runnable” means

`program.py` must run the host-level program deterministically and may call device code only through stable runtime
shims, enabling:

- `mode="sim"`: backend simulator / reference interpreter (may be slow)
- `mode="device"`: binding loads `codegen/<backend>/...` artifacts and executes

If a stage relies on an external toolchain artifact that cannot be simulated faithfully, the stage must still be runnable
via explicit stubs (`RunnablePyStubbed`) and must emit diagnostics and stub metadata.

---

## 6) Replay generation contract (what passes must preserve)

Because “runnable Python at every stage” is a core differentiator, HTP needs an explicit contract for how
`ir/stages/<id>/program.py` is produced.

Normative v1 contract:

- `program.py` is generated from the stage’s canonical AST plus `env.json`.
- device-level computation is routed through stable runtime shims:
  - `htp.runtime.call_kernel(...)`
  - `htp.runtime.intrinsics.*` (portable simulation stubs when possible)
- extension packages may add backend/toolchain-specific replay helpers, but the stage generator may only call them
  through HTP’s extension hook mechanism rather than hard-coding MLIR or vendor-specific APIs into the core runtime
- when a region is only available as an extension-owned artifact or toolchain output, the replay program routes through
  explicit reference semantics or a structured sim stub (never “missing replay”)

The pass contract must state whether it preserves or stubs this property (`RunnablePy` in
`docs/design/impls/02_pass_manager.md`).

HTP’s design constraint is stronger than “best effort replay”:

> All stages must be runnable in `mode="sim"`.

Therefore, passes are not allowed to “drop replay” by omitting `program.py`. When a stage cannot faithfully simulate an
accelerated region, it must remain runnable by:

- routing the region through a runtime shim with a sim fallback, or
- using an explicit stub that raises a structured diagnostic at runtime (still importable/executable).

Recommended stub metadata file:

- `ir/stages/<id>/replay/stubs.json`

Minimum contents:

- `schema`: `htp.replay.stubs.v1`
- one entry per stubbed region/intrinsic with:
  - `node_id`
  - `entity_id` (when available)
  - `kind`: `intrinsic | external_toolchain | island_adapter | intentionally_unimplemented`
  - `diagnostic_code`
  - `artifact_ref` (if tied to emitted backend artifacts)

### 6.1 Normative v1 replay module shape

Every generated stage module must expose the same entry surface so bindings and agents do not need per-stage adapters:

- `STAGE_INFO`: static dict containing:
  - `stage_id`
  - `def_id`
  - `runnable_py`: `preserves | stubbed`
  - `supported_modes`: always includes `sim`
- `def run(*args, mode="sim", runtime=None, trace=None, **kwargs):`
  - the canonical stage entry used by bindings for replay
- optional helpers generated from the AST (private to the module), but no custom public entry surface

Normative behavior:

- `run(..., mode="sim")` must execute without requiring backend binaries to exist.
- `run(..., runtime=None)` must default to `htp.runtime.default_runtime()`.
- if the stage is marked `stubbed`, reaching a stubbed region must raise a structured replay diagnostic, not an arbitrary
  Python exception.

### 6.2 Normative v1 runtime shim surface

To keep replay stable, HTP needs a small, fixed runtime surface. The v1 stage generator is allowed to call only:

- `htp.runtime.default_runtime() -> Runtime`
- `htp.runtime.call_kernel(kernel_id, *, args, mode, artifacts, trace=None) -> object`
- `htp.runtime.intrinsics.invoke(name, *, args, attrs=None, mode, trace=None) -> object`
- `htp.runtime.extensions.invoke(extension_id, operation, *, payload, mode, trace=None) -> object`
- `htp.runtime.raise_stub(code, *, node_id, entity_id=None, kind, artifact_ref=None, detail=None) -> None`

Required semantics:

- `call_kernel(...)`
  - in `sim`, dispatches to reference semantics or backend simulator;
  - in `device`, dispatches through the selected binding/runtime.
- `intrinsics.invoke(...)`
  - dispatches to intrinsic simulator handlers in `sim`;
  - when no simulator exists but a stub policy is declared, it must call `raise_stub(...)`.
- `extensions.invoke(...)`
  - is the native escape hatch for optional extension packages and external toolchain adapters;
  - core HTP does not ship MLIR semantics in the runtime surface; extension packages own their own operation names and
    payload schemas behind this hook.
- `raise_stub(...)`
  - must raise a stable replay diagnostic rather than a raw exception.

This API is intentionally small. If a new internal IR construct cannot replay through this surface, it is not yet a
valid HTP stage construct.

---

## 7) Metadata requirements (minimum)

- serializable for artifact dumps
- stable node identity scheme (see above)
- no reliance on Python object identity across processes
