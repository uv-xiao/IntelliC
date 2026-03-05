# Impl: IR Model (AST-first + typed metadata)

## Goal

Define the minimal internal representation strategy that preserves Python extensibility.

This design deliberately exploits a Python-specific advantage: because the IR is Python AST, every intermediate stage can
also emit a **runnable Python program** (host/orchestration level) for replay, simulation, and debugging.

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

## 4) Dump schema and replay program (`RunnablePy`)

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

## 5) Metadata requirements (minimum)

- serializable for artifact dumps
- stable node identity scheme (see above)
- no reliance on Python object identity across processes
