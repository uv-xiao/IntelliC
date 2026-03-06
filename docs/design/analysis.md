# HTP (Heterogeneous Tile Programming) — Redo Design (WHY)

## 0. Summary

This document repositions the project from “PTO-WSP” (a single-ISA-centric name) to **HTP: Heterogeneous Tile Programming**: a Python-native framework to author **kernels → megakernels → serving routines** and to compile them into **inspectable artifacts** for multiple heterogeneous backends (Ascend PTO toolchain/runtime, AIE/MLIR-AIE, and future targets).

The redo’s core thesis:

1. **Extensibility is the primary product**, not a secondary plugin hook.
2. Extensibility only works if the framework can **type-check composition across extensions** (dialects, intrinsics, layouts, passes, pipelines, backends, bindings).
3. Therefore HTP must be designed as an **AST-first, artifact-first, capability-typed compiler framework**, not as an incremental evolution of a single-backend compiler.

This is a docs-only design under `docs/design/`.

---

## 1. Positioning (what HTP is)

HTP is a **programming + compilation** framework with three roles:

1. **Programming entry**: Python authoring for:
   - Tile kernels (device-level compute/data movement)
   - Megakernels (fused and/or multi-stage kernels)
   - Serving routines (host-side orchestration + pipelines + scheduling)
2. **Compilation**: a Python-driven pipeline starting from **Python AST**, with:
   - pass pipelines over AST (match/apply) as the default extensibility unit
   - optional “external compiler islands” (e.g., MLIR pipelines) triggered from AST passes
3. **Artifact & binding**: compilation emits a backend-specific **artifact tree** + manifest; binding loads/executes artifacts via backend runtimes/toolchains.

HTP is not a single IR/ISA project. PTO, MLIR-AIE, and future targets are **backends**.

HTP also treats **LLM-based compiler development** as a native target of the framework:

- artifact packages, traces, and diagnostics are designed to be *machine-consumable*, not only human-readable,
- intermediate programs are replayable (sim) so agents can verify behavior stage-by-stage,
- and extension surfaces are bounded so autonomous edits remain safe and reviewable.

## 1.1 Naming and repo reality (docs-only)

This redo uses the name **HTP** consistently in design documents to reflect the multi-backend, multi-level ambition.

- The repository and Python module may still be named `pto-wsp` / `pto_wsp` today.
- This redo does not rename code; it establishes the *target architecture* and terminology.
- A future execution plan must provide:
  - a new `htp` package,
  - remove all `pto_wsp`s,
  - no deprecated allowed, all removed.

---

## 2. Problem statement (why redo)

The v9-era framing (“PTO-WSP”) anchors the project identity to PTO ISA and to one workload/schedule model. That framing is misaligned with the actual ambition:

- **Multi-backend**: Ascend simulation/device + AIE + future accelerator targets.
- **Multi-level**: kernel → megakernel → serving routine, not only kernel-like codegen.
- **Multi-model**: both **WSP** (workload/schedule programming) and **CSP** (process/channel pipelines), plus future models.

If the framework is redesigned as “a compiler with plugins”, extensions will collide:

- a backend wants a particular intrinsic set,
- the intrinsic set expects a certain layout facet,
- a pass expects a certain AST shape and attaches new metadata,
- the pipeline must select only compatible passes,
- the binding expects a specific artifact contract.

Without a unifying design, “extensibility” becomes a combinatorial explosion of ad-hoc checks.

Equally important: without an agent-native substrate, the project’s evolution becomes brittle.
Real compiler work is:

- long-horizon (months of incremental feature work),
- multi-surface (front-end, analyses, transforms, backends, runtimes),
- and regression-prone (implicit invariants).

If “LLM agents as maintainers” is an intended mode of development, the framework must encode explicit invariants and leave
verifiable evidence by construction; otherwise agents (and humans) are forced into pass-order folklore and partial logs.

---

## 3. Design methodology (how we redo it)

### 3.1 AST-first: Python AST is the source IR

HTP’s front-end unit is Python code, and the default compiler substrate is **Python AST with typed annotations**.

- Dialects (WSP, CSP, etc.) are represented as *AST constructs + metadata*, not as “one monolithic IR”.
- The pass system is primarily **AST mutators** using *match → apply*.
- Optional external IRs (e.g., MLIR) are “islands”: they are entered/exited by explicit AST passes.

Rationale:

- Python is the extension language; AST is the natural unit for interception.
- Most user-facing “programming model extensions” are syntax/semantics transformations.

### 3.2 Artifact-first: compilation produces an inspectable package

Every compile produces a directory tree that is:

- **reviewable** (IR snapshots, pass traces),
- **reproducible** (manifest includes inputs, pipeline, versions),
- **runnable** (contains backend-emittable and/or backend-executable artifacts).

Rationale:

- Practical debugging: users need to see what the compiler emitted.
- Cross-team integration: runtime teams consume artifact contracts.

#### 3.2.1 Stage replay is the “verifiable intermediate artifact” (essential for agents)

Artifact-first becomes qualitatively stronger when intermediate artifacts are **executable**, not only inspectable.
HTP therefore treats stage replay as a hard design constraint:

- every stage emits `ir/stages/<id>/program.py`, and
- every stage program is runnable in `mode="sim"` (possibly stubbed with explicit diagnostics for accelerated regions).

This matters for agent-based (and human) compiler development because it creates an objective, automatable truth source:

- **A stage is a test oracle**: an agent can replay `sN` and `sN+1` to check whether a transform preserved semantics for a
  chosen set of observable behaviors, without depending on internal compiler state.
- **Regression localization is mechanical**: “the first bad stage” can be found by replay/bisect over stage programs.
- **Intermediate evidence is portable**: a stage program is a plain Python entrypoint plus staged metadata/analyses, which
  makes it suitable as a “context pack” for autonomous loops and for cross-team debugging.

Design implication: intermediate IR forms and extensions must remain executable (typically by lowering internal constructs
to runtime shim calls with sim semantics). External toolchains (MLIR islands, vendor compilers) become accelerators
attached to stages, not semantic owners of the program.

#### 3.2.2 Agent-native by construction (machine-consumable contracts)

To treat LLM-based development as a first-class target, HTP must design *every important interface* as structured data:

- **pass trace is structured** (`ir/pass_trace.jsonl`) and references staged dumps, not ad-hoc text logs
- **diagnostics are machine-localizing** (stable code + `node_id` + structured payload ref)
- **analyses are staged** (`ir/stages/<id>/analysis/*`) and versioned (no “hidden RAM caches”)
- **provenance is explicit** (`extensions.agent.*` in the manifest) so autonomous work is auditable and repeatable

This is not extra tooling; it is the only way to make autonomous edits healthy over time.

### 3.3 Capability-typed composition: extensibility with correctness

HTP’s “glue” is a **capability/type system** that makes extension composition checkable:

- Dialects provide/require capabilities (e.g., “CSP graph”, “WSP schedule directives”).
- Intrinsic libraries declare required layout/hardware capabilities.
- Layout facets are typed objects with join/compatibility rules.
- Passes and pipelines declare `requires` / `provides`.
- Backends declare supported capabilities + required manifest fields.
- Bindings declare which artifact contracts they can load/execute.

Compilation becomes:

1. Build a “program capabilities” view from the AST.
2. Select a pipeline whose pass requirements are satisfiable.
3. Type-check layout/stream effects and backend compatibility.
4. Emit artifacts that satisfy the binding contract.

This is the only scalable way to keep “define anything” extensibility while preventing broken combinations.

---

## 4. Foundational concepts (the minimum stable core)

HTP’s stable core should be minimal, but strong:

1. **Program**: a Python module/function set with declared entrypoints and dialect enablement.
2. **Dialect**: a named semantic layer represented in AST + metadata (e.g., WSP, CSP).
3. **Intrinsic set**: a library of typed primitives with backend handlers (e.g., PTO intrinsics).
4. **Layout**: a unified representation with facets:
   - Distribution facet (Dato/Axe-style sharding/replication, collectives)
   - Memory facet (Triton/CuTe-style strides/order/swizzle/pack)
   - Hardware facet (Arknife-style hierarchy + memory spaces constraints)
5. **Pass**: a transformation with explicit contracts (`requires/provides`, invariants).
6. **Pipeline**: an ordered pass set producing a backend artifact contract.
7. **Backend**: a codegen target describing hardware model + artifact contract.
8. **Binding**: the “build/load/run” adapter for a backend artifact package.

Everything else is extension territory.

---

## 5. Success criteria (what “good” looks like)

1. **Extension authoring is straightforward**:
   - “Add a new dialect” does not require rewriting the whole compiler.
   - “Add a new backend” is primarily writing a new pipeline + emitter + binding contract.
2. **Composition is safe**:
   - Incompatible combinations are rejected early with actionable diagnostics.
3. **Artifacts are the integration boundary**:
   - Runtime teams can rely on stable manifests and package shape.
4. **Debuggability is first-class**:
   - Pass snapshots, IR dumps, and trace hooks are standard.
5. **Replay is universal in sim**:
   - Any intermediate stage can be replayed in `mode="sim"` to provide verifiable evidence for transforms and to localize
     regressions (critical for long-term autonomous development).

---

## 6. Non-goals (to keep HTP sane)

1. Not a general-purpose Python compiler.
2. Not an MLIR-only framework; MLIR is optional and backend-specific.
3. Not a single “universal IR” that tries to represent every backend perfectly.
4. Not a full automatic schedule search system (may be added later as an extension).

---

## 7. Reading map (this redo set)

- `docs/design/features.md` — feature catalog and rationale (WHAT)
- `docs/design/implementations.md` — architecture and component design (HOW)
- `docs/design/story.md` — cohesive end-to-end narrative (WHY→WHAT→HOW)
- `docs/design/examples.md` — end-to-end examples across backends
- `docs/design/feats/` — deep dives per feature
- `docs/design/impls/` — deep dives per implementation component
