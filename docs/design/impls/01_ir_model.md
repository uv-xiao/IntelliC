# Impl: IR Model (AST-first + typed metadata)

## Goal

Define the minimal internal representation strategy that preserves Python extensibility.

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
   - for AIE: MLIR-AIE module(s) as an island product

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
3) **External toolchains are accelerators, not semantic owners**.
   - Entering an external island (MLIR-AIE, vendor compilers, etc.) cannot delete the program’s sim semantics. The stage
     must remain runnable by keeping (or reconstructing) a Python-level executable representation and by routing island
     calls through a runtime shim with a sim fallback.

Practically, HTP must define an explicit “executable subset” of Python AST plus a small, stable runtime API that gives
semantics to IR-level operations.

---

## 2) Node identity (stable IDs)

HTP must not rely on Python object identity. Every AST node that can appear in diagnostics, dumps, or traces needs a
stable `node_id`.

Recommended scheme (deterministic within a stage):

- `symbol_path`: canonical symbol path of the owning definition (e.g. `module::add::add_tile`)
- `kind`: node kind tag (e.g. `Call`, `For`, `KernelDef`, `ChannelSend`)
- `ordinal`: deterministic pre-order index within the owning definition after canonicalization
- `span`: `(file, line, col)` when available (debug only; not a primary key)

`node_id = f"{symbol_path}:{kind}:{ordinal}"`

When a pass performs major rewrites, it may optionally emit a `node_id_map.json` for “semantic diff” tools, but stable IDs
within each stage are sufficient for traceability.

---

## 3) Metadata attachment model

Typed metadata is stored separately from the AST structure and keyed by `node_id` and symbol paths:

- `types`: inferred types (tile/tensor/buffer/scalars)
- `layout`: facet product values (distribution/memory/hardware)
- `effects`: protocol obligations (channels, async tokens, barriers, collectives)
- `schedule`: schedule directives and their resolved/unsatisfied constraints

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

If a stage contains an external compilation island that cannot be simulated, the stage may still be runnable via stubs
(`RunnablePyStubbed`) and must emit diagnostics and stub metadata.

---

## 6) Replay generation contract (what passes must preserve)

Because “runnable Python at every stage” is a core differentiator, HTP needs an explicit contract for how
`ir/stages/<id>/program.py` is produced.

Recommended contract:

- `program.py` is generated from the stage’s canonical AST plus `env.json`.
- device-level computation is routed through stable runtime shims:
  - `htp.runtime.call_kernel(...)`
  - `htp.runtime.intrinsics.*` (portable simulation stubs when possible)
- when a region is lowered into an external island (MLIR-AIE, vendor toolchains, etc.), the replay program calls an
  island stub:
  - `htp.runtime.islands.invoke(island_id, ...)`

The pass contract must state whether it preserves or breaks this property (`RunnablePy` in
`docs/design/impls/02_pass_manager.md`).

HTP’s design constraint is stronger than “best effort replay”:

> All stages must be runnable in `mode="sim"`.

Therefore, passes are not allowed to “drop replay” by omitting `program.py`. When a stage cannot faithfully simulate an
accelerated region, it must remain runnable by:

- routing the region through a runtime shim with a sim fallback, or
- using an explicit stub that raises a structured diagnostic at runtime (still importable/executable).

---

## 7) Metadata requirements (minimum)

- serializable for artifact dumps
- stable node identity scheme (see above)
- no reliance on Python object identity across processes
