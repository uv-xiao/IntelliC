# Impl: Capability Solver (pipeline satisfiability + explainable failure)

## Goal

Make “can this program be compiled to this target under these extensions?” a **checkable contract**, not a best-effort
attempt that fails late in backend lowering.

The solver replaces two failure-prone patterns:

- backend-specific `if/else` pipeline branching, and
- implicit pass ordering “tribal knowledge”

with a small, explicit constraint language over capabilities, layout/effect invariants, and required artifact outputs.

---

## 1) What a “capability” is (minimum definition)

A **capability** is a stable, comparable tag that denotes a fact about the current compilation state, such as:

- “WSP dialect is enabled”
- “layout facets are normalized”
- “analysis X exists at version V”
- “target provides async copy of kind K with scope S”

Recommended representation:

- `Capability(tag, params)` where:
  - `tag` is namespaced, e.g. `Dialect.WSPEnabled`, `Arch.AsyncCopy`, `Analysis.WarpRolePlan`
  - `params` are a small, JSON-serializable map, e.g. `{ "scope": "group_shared", "kind": "token" }`

Capabilities are not a substitute for semantic proofs; they are the *routing and composability substrate* for passes,
pipelines, and backend integrations.

---

## 2) Inputs

### 2.1 Program facts

Derived from:

- enabled dialect packages
- imported intrinsic sets
- AST-derived requirements (effects/layout obligations)
- already materialized analyses (when the pipeline is resumed)

### 2.2 Target facts

Declared by the backend `ArchModel`:

- hierarchy and subgroup kinds (if any)
- memory spaces and legality constraints
- async primitives and barrier/event model
- supported intrinsic handlers (lower/emit/simulate)

### 2.3 Pipeline template

Includes:

- ordered pass list (each with `requires/provides/invalidates` + invariants)
- output artifact contract requirements
- replay requirements (e.g. “must preserve runnable Python in sim mode until stage sN”)
- pass parameters (fixed or solver-bound)

---

## 3) Outputs

One of:

1) a satisfiable **pipeline instance** (pass parameters bound, optional choices resolved), or
2) a structured, explainable **failure report** that points to the smallest contract boundary that prevents compilation.

The solver’s job is not “pick the fastest pipeline”; its baseline job is:
> reject impossible pipelines early with actionable reasons.

---

## 4) Baseline algorithm: forward checking (deterministic)

Start with a deterministic forward-checking solver:

1) compute initial `CapabilityState` from:
   - dialect packages and their declared capabilities
   - intrinsic sets and handler availability for the target
   - required layout/effect invariants inferred from the AST (obligations)
   - target backend capability declarations (ArchModel)
2) walk the pipeline passes in order:
   - verify `requires` is satisfied by current capabilities + invariants
   - verify required analyses exist (`analysis_requires` in the pass contract)
   - apply `provides` and `invalidates` to the capability state
3) verify final artifact contract requirements:
   - required `codegen/<backend>/...` outputs exist in the pipeline’s declared outputs
   - required replay properties are satisfied (`RunnablePy` modes; see `docs/design/impls/02_pass_manager.md`)

If any step fails, emit a failure report that points to:

- *what* is missing (capability / invariant / handler / artifact output),
- *where* it became missing (which pass boundary),
- and *how* it could be provided (candidate providers, when known).

---

## 5) Handling analysis capabilities (important for long-term correctness)

Analyses are treated as explicit capabilities:

- a pass that produces `warp_role_plan@1` provides `Analysis.WarpRolePlan@1`
- a pass that consumes it requires `Analysis.WarpRolePlan@1`

When a transform pass mutates AST, it should invalidate analyses conservatively unless it explicitly preserves them:

- `invalidates: { Analysis.* }` (broad) or `invalidates: { Analysis.LoopDeps@1 }` (targeted)

This is how the solver prevents “stale analysis reuse” across long pipelines.

Worked example of analysis + transform staging:

- `docs/design/impls/11_case_study_warp_specialization_pipelining.md`

---

## 6) Failure report schema (recommended)

Emit a structured report (path recorded in the manifest), e.g. `ir/solver_failure.json`:

- `schema`: `htp.solver_failure.v1`
- `pipeline`: name/template id
- `failed_at_pass`: pass id (or `final_contract`)
- `missing_caps`: list of missing capability tags (with params)
- `missing_handlers`:
  - intrinsic ids that lack `lower|emit|simulate` handlers for the target backend
- `layout_conflicts`:
  - list of facet predicate conflicts with example node ids and relevant layout snapshots
- `undischarged_effects`:
  - list of remaining obligations with example node ids and effect snapshot pointers
- `artifact_contract_violations`:
  - missing required output kinds and expected paths
- `providers`:
  - candidate passes/packages that could provide missing caps (if registered)
- `unsat_core` (best effort):
  - a minimal list of requirements that cannot be jointly satisfied (when derivable)
- `hints`:
  - human-readable suggestions (optional; tools must not depend on them)

This file is a first-class debugging substrate for humans and agents: it is the “explainable unsat core”.

---

## 7) Future extensions (solver evolution without breaking contracts)

The baseline solver is forward checking. Extensions can be layered without changing the pass contracts:

### 7.1 Alternative choices (OR nodes)

Allow pipeline templates to declare choices:

- “use pipeliner A or B depending on target capability”
- “use island lowering when backend supports it”

The solver then performs bounded search, still emitting explainable failure when no choice satisfies constraints.

### 7.2 Cost models (optional)

Once satisfiable, selection can be optimized by a cost model:

- compile-time cost (fast pipelines for iteration)
- runtime estimates (perf pipelines for deployment)
- debug constraints (preserve runnable Python deeper)

Crucially, cost-based selection is layered on top of satisfiability; it never replaces contract checking.
