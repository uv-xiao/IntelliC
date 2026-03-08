# HTP Future Gap Checklist

This file tracks the **true remaining gaps** between the current codebase and
the broader target described under `docs/future/`.

It is intentionally operational:

- `[x]` means the capability exists in code today
- `[~]` means there is a partial landing, but the broader future contract is not complete
- `[ ]` means the future contract is not implemented yet

Use this file as the tracking surface for future feature branches.

---

## 0. Landed baseline (not gaps)

These items are already implemented and should **not** be re-added as future
work:

- `[x]` staged Python replay artifacts under `ir/stages/`
- `[x]` staged semantic payloads: `kernel_ir`, `workload_ir`, `types`,
  `layout`, `effects`, `schedule`
- `[x]` pass contracts and pass trace emission
- `[x]` solver preflight plus `ir/solver_failure.json`
- `[x]` package tooling: `htp replay`, `htp verify`, `htp diff --semantic`,
  `htp explain`
- `[x]` MLIR CSE extension package path
- `[x]` AIE artifact-emission extension path
- `[x]` PTO `a2a3sim` numerical path
- `[x]` NV-GPU CUDA numerical path

The remaining sections below are the **actual open gaps**.

---

## 1. Solver and composition layer

Source intent:

- `docs/future/impls/03_capability_solver.md`
- `docs/future/feats/01_extensibility.md`
- `docs/future/feats/06_passes_pipelines.md`

Current code anchors:

- `htp/solver.py`
- `htp/compiler.py`
- `htp/pipeline/defaults.py`

Checklist:

- `[~]` Solver exists, but pipeline templates are still effectively a single
  hard-coded default template.
- `[x]` Move backend capability facts out of local solver tables and into
  backend-owned declarations (`ArchModel`-style source of truth).
- `[~]` Make extension-provided passes and extension-provided pipelines
  first-class solver inputs rather than ad-hoc extension-specific checks.
- `[x]` Use `PassContract.requires_layout_invariants` and
  `PassContract.requires_effect_invariants` as real satisfiability checks rather
  than dormant fields.
- `[x]` Use `PassContract.establishes_layout_invariants` and
  `PassContract.establishes_effect_invariants` in the evolving capability state
  beyond simple accumulation.
- `[x]` Record solver satisfaction details into `ir/pass_trace.jsonl`
  (`requires_satisfied`) instead of leaving them empty.
- `[~]` Emit solver-visible candidate providers from actual registered passes and
  extensions rather than best-effort local hints.
- `[~]` Add bounded alternative choice support (OR nodes) for pipeline
  selection.
- `[ ]` Add cost-model-based selection only after satisfiability is complete.
- `[~]` Unify final artifact requirements with backend/extension contracts so
  the solver does not maintain a second independent list.
- `[x]` Make solver-visible resumption work from existing artifact packages, not
  only from fresh in-memory compilation inputs.
- `[x]` Add tests for mixed core+extension pipeline selection rather than only
  default-pipeline satisfiability.

---

## 2. Agent-facing tooling and autonomous development loop

Source intent:

- `docs/future/impls/10_agentic_tooling.md`
- `docs/future/feats/10_agentic_development.md`

Current code anchors:

- `htp/tools.py`
- `htp/__main__.py`
- `manifest.json` `extensions.agent.*`

Checklist:

- `[~]` `htp replay`, `htp verify`, `htp diff --semantic`, and `htp explain`
  exist, but they are still thin utilities rather than a full agent-product
  surface.
- `[x]` Add `htp minimize <package>` to reduce failing packages to smaller
  reproducers.
- `[x]` Add stage bisect/localization tooling on top of replay so agents can
  find the first divergent stage automatically.
- `[~]` Extend `htp diff --semantic` from current-stage JSON comparison to
  staged identity-aware semantic diffs.
- `[x]` Add a real diagnostic catalog with stable fix-hint policies rather than
  a small hard-coded explanation table.
- `[x]` Add agent policy input (for example `agent_policy.toml`) covering:
  allowed edit roots, required gates, promotion mode, and perf thresholds.
- `[x]` Extend provenance under `extensions.agent.*` to include:
  decision trace, attempted candidates, rejected candidates, patch summary, and
  timing.
- `[ ]` Add promotion workflow support (patch-only / PR / auto-land) without
  placing git policy inside core compiler passes.
- `[x]` Add artifact-based golden diff gates into `verify_package(...)`, not
  just validate + replay.
- `[ ]` Add target-specific correctness suites into `verify_package(...)` rather
  than leaving them as external test selection.
- `[ ]` Add optional performance gates and threshold policy to the tool surface.
- `[ ]` Add bounded edit-corridor templates for passes, intrinsic handlers, and
  backend contracts to support healthy autonomous changes.

---

## 3. Core type system and semantic model breadth

Source intent:

- `docs/future/features.md`
- `docs/future/feats/04_intrinsics.md`
- `docs/future/feats/05_layout.md`

Current code anchors:

- `htp/ir/semantics.py`
- `htp/ir/op_specs.py`
- `htp/passes/program_model.py`

Checklist:

- `[~]` The typed substrate now includes structured scalar/shape/buffer/view/channel/token
  payloads, but it still does not cover the full shared user-facing type system.
- `[~]` Introduce a real shared type surface for:
  `i8/i16/i32/i64/u*/f16/bf16/f32/f64/bool`.
- `[~]` Add first-class `Index`, `Dim`, and symbolic shape constructs rather
  than storing symbolic dimensions as bare strings.
- `[x]` Add explicit value kinds for:
  tiles, tensors, buffers, views, async tokens, and channel handles.
- `[x]` Add first-class buffer/view alias modeling rather than inferring only
  from names.
- `[x]` Move from op-name heuristics to a fuller op registry that covers:
  load, store, cast, broadcast, transpose/view, reduction, async copy, barrier,
  await, mma, and channel ops.
- `[x]` Support reduction semantics as first-class kernel IR, not just as a
  future idea.
- `[x]` Support view/reshape/transpose semantics explicitly in the semantic
  model and stage payloads.
- `[~]` Support collective/distribution-facing operations in the semantic model.
- `[x]` Add legality checks for aliasing and mutation patterns, not only simple
  dtype/backend checks.
- `[x]` Replace stringly buffer type encodings like `f32[MxK]` with structured
  shape/dtype payloads in staged types.

---

## 4. Layout, effects, schedule, and protocol typing

Source intent:

- `docs/future/feats/05_layout.md`
- `docs/future/feats/03_dialects_csp.md`
- `docs/future/feats/09_debuggability.md`

Current code anchors:

- `htp/passes/program_model.py`
- `htp/passes/typecheck_layout_effects.py`
- `htp/passes/analyze_schedule.py`

Checklist:

- `[~]` Layout/effects/schedule are emitted today, but they are still simple
  synthesized metadata rather than the full typed contract model.
- `[~]` Implement the facet-product layout model:
  distribution ⊗ memory ⊗ hardware.
- `[ ]` Add explicit relayout operations and legality predicates rather than
  backend heuristics only.
- `[ ]` Add distribution joins / shard / replicate semantics as typed layout
  facts.
- `[~]` Add collective-effect obligations and discharge rules.
- `[x]` Upgrade channel effects from producer/consumer annotation to typed
  protocol obligations.
- `[~]` Add deadlock-prevention checks for channel/process protocols rather than
  only local channel metadata.
- `[~]` Model async tokens, barrier scopes, and event dependencies explicitly in
  effects.
- `[x]` Make schedule state carry real directives:
  mapping, specialization, pipelining depth, buffering strategy, warp-role
  plan, launch structure.
- `[x]` Add schedule legality checks against hardware/layout constraints rather
  than generating a plan opportunistically.
- `[ ]` Keep structured node/entity references in diagnostics for layout/effect
  violations throughout this richer model.

---

## 5. WSP and CSP dialect packages

Source intent:

- `docs/future/feats/02_dialects_wsp.md`
- `docs/future/feats/03_dialects_csp.md`

Current code reality:

- There are no first-class WSP or CSP dialect packages in `htp/` today.

Checklist:

- `[x]` Add a real WSP dialect package with user-facing authoring surface.
- `[x]` Add canonical WSP lowering into the shared semantic substrate.
- `[x]` Add explicit schedule directives rather than treating scheduling as a
  hidden analysis transform.
- `[x]` Add a real CSP dialect package with typed processes and channels.
- `[x]` Add canonical CSP lowering into the shared semantic substrate.
- `[x]` Add typed channel capacity, element type, and protocol contracts.
- `[ ]` Add process/channel effect checking integrated with the solver.
- `[~]` Add examples and tests that demonstrate WSP and CSP as extension-owned
  front-end surfaces, not only backend-oriented package construction.

---

## 6. Intrinsic system and handler registration

Source intent:

- `docs/future/feats/04_intrinsics.md`

Current code anchors:

- `htp/intrinsics.py`
- `htp/runtime/core.py`
- `htp/runtime/intrinsics.py`
- `htp/backends/nvgpu/lower.py`
- `htp/backends/pto/lower.py`

Checklist:

- `[x]` Add an explicit `IntrinsicDecl` contract surface.
- `[~]` Split portable intrinsics from backend intrinsics in the registry.
- `[x]` Add handler registration for `lower`, `emit`, and `simulate`.
- `[x]` Add explicit stub-policy declarations per intrinsic/target.
- `[x]` Move backend handler availability checks from op-name tables to
  intrinsic-handler declarations.
- `[~]` Add callable lower/sim dispatch through the registry rather than using
  the registry only as a boolean capability table.
- `[~]` Add typed effect contracts for async copy, barriers, tokens, and
  collectives at the intrinsic level.
- `[ ]` Add extension-owned intrinsic packages under stable registration
  surfaces.

---

## 7. Pass system and pipeline ecosystem

Source intent:

- `docs/future/feats/06_passes_pipelines.md`
- `docs/future/impls/11_case_study_warp_specialization_pipelining.md`

Current code anchors:

- `htp/passes/*`
- `htp/passes/manager.py`

Checklist:

- `[~]` Pass contracts and staged analyses exist, but the default pass spine is
  still small and compiler-owned.
- `[ ]` Add first-class pass package registration beyond the current built-in
  modules.
- `[ ]` Add pipeline template registration beyond the current default template.
- `[ ]` Add extension-owned passes that consume and produce the same staged
  contract surfaces as core passes.
- `[ ]` Add richer transform examples such as warp specialization and software
  pipelining as real passes, not only design docs.
- `[ ]` Add staged analysis payloads for warp-role plans, pipeline plans, loop
  dependencies, and async/resource checks.
- `[ ]` Add preservation/invalidation tracking beyond simple capability removal.
- `[ ]` Thread solver satisfaction and pass trace together so the trace shows
  why each pass was legal.

---

## 8. MLIR round-trip island expansion

Source intent:

- `docs/future/impls/12_mlir_roundtrip_island.md`

Current code anchors:

- `htp_ext/mlir_cse/export.py`
- `htp_ext/mlir_cse/import_.py`
- `htp_ext/mlir_cse/island.py`
- `htp/passes/manager.py`

Checklist:

- `[~]` The MLIR CSE extension proves the boundary, but it is still narrow.
- `[ ]` Convert the MLIR extension from a standalone package emitter into a
  proper pass/pipeline participant where appropriate.
- `[ ]` Add the full v1 island artifact set:
  `input.mlir`, `output.mlir`, `pipeline.txt`, `ledger.json`,
  `eligibility.json`, `import_summary.json`.
- `[ ]` Record the exact MLIR pass pipeline used, not only the net result.
- `[ ]` Parse and import real transformed MLIR rather than doing Python-side CSE
  and treating MLIR as a side artifact.
- `[ ]` Implement explicit eligible-subset matching over canonical typed program
  structure, not only scalar elementwise kernel normalization.
- `[ ]` Add `entity_map.json` and `binding_map.json` emission for non-trivial
  rewrites.
- `[ ]` Preserve or rebind identities according to the import policy described
  in the future docs.
- `[ ]` Add malformed-island validation and round-trip correctness tests.
- `[ ]` Make solver-visible extension composition cover MLIR island entry/exit
  requirements, not only a yes/no eligibility bit.

---

## 9. Backend and runtime gaps

Source intent:

- `docs/future/feats/07_backends_artifacts.md`
- `docs/future/feats/08_binding_runtime.md`
- `docs/future/impls/06_backend_aie.md`

### 9.1 PTO

Current code anchors:

- `htp/backends/pto/*`
- `htp/bindings/pto.py`
- `htp/bindings/pto_runtime_adapter.py`

Checklist:

- `[~]` PTO has a real `a2a3sim` path, but the semantic/codegen surface is
  still narrow.
- `[ ]` Add real PTO support beyond single elementwise numerical kernels.
- `[ ]` Add richer kernel/workload lowering for channels, async, and multi-task
  orchestration.
- `[ ]` Add stronger device-mode (`a2a3`) execution coverage and tests.
- `[ ]` Add solver-visible PTO capability declarations from backend-owned data.
- `[ ]` Add broader artifact and runtime validation for non-trivial PTO package
  shapes.

### 9.2 NV-GPU

Current code anchors:

- `htp/backends/nvgpu/*`
- `htp/bindings/nvgpu.py`
- `htp/bindings/nvgpu_cuda_adapter.py`

Checklist:

- `[~]` NV-GPU has a real CUDA path, but still only a narrow operation surface.
- `[ ]` Add broader kernel lowering beyond elementwise and naive matmul.
- `[ ]` Add explicit Blackwell-specific capability/profile differences beyond
  profile naming.
- `[ ]` Add alternate adapter paths such as `nvrtc` where the design calls for
  adapter choice.
- `[ ]` Add profiling/perf-report integration into the binding-owned execution
  path.
- `[ ]` Add richer launch-geometry and memory-space semantics than current
  heuristics.

### 9.3 AIE

Current code anchors:

- `htp_ext/aie/emit.py`
- `htp/bindings/aie.py`

Checklist:

- `[~]` AIE artifact emission exists, but it is still a contract skeleton.
- `[ ]` Split AIE into planning analyses and emission transforms.
- `[ ]` Add solver-visible AIE capabilities.
- `[ ]` Emit richer MLIR-AIE content derived from real mapping/FIFO plans rather
  than placeholder MLIR comments.
- `[ ]` Add host/runtime integration beyond replay-only validation.
- `[ ]` Add toolchain execution and validation for the emitted AIE package.
- `[ ]` Add end-to-end examples that exercise mapping and FIFO semantics.

### 9.4 Additional extension backends

- `[ ]` Define and implement the next backend after AIE, if still desired.
- `[ ]` Ensure new backends consume shared semantic contracts rather than
  introducing backend-owned compiler sub-architectures.

---

## 10. Manifest, artifact contract, and validation closure

Source intent:

- `docs/future/acceptance_checklist.md`
- `docs/future/feats/07_backends_artifacts.md`
- `docs/future/feats/09_debuggability.md`

Current code anchors:

- `htp/artifacts/*`
- `htp/bindings/validate.py`
- backend bindings

Checklist:

- `[~]` Manifest and stage graphs exist, but the future docs still describe a
  richer closure than current code implements.
- `[ ]` Add manifest-level inputs/pipeline/capabilities recording beyond the
  current minimal shape.
- `[ ]` Validate more than stage graph paths at the generic validation layer
  where appropriate.
- `[ ]` Make artifact ownership and validation rules fully shared between
  emitters, solver, and bindings.
- `[ ]` Add structured schema/version validation for more emitted sidecars.
- `[ ]` Strengthen staged semantic diff support around identities and maps.
- `[ ]` Make replay/stub metadata richer and easier to diff automatically.

---

## 11. Debuggability and diagnostics

Source intent:

- `docs/future/feats/09_debuggability.md`

Current code anchors:

- `htp/runtime/errors.py`
- bindings and tool APIs

Checklist:

- `[~]` Structured diagnostics exist, but the broader debug contract is not
  complete.
- `[ ]` Make diagnostics consistently include `node_id`, payload refs, and fix
  hint refs across compiler, bindings, and extensions.
- `[ ]` Add richer diagnostic families for layout conflicts, protocol
  violations, and solver unsat cores.
- `[ ]` Add first-class semantic diff tooling across stages and packages using
  identities and maps, not only JSON inequality.
- `[ ]` Add standardized trace/log schemas for backend build/run adapters.
- `[ ]` Add explicit debug guidance for extension-owned islands and backend
  toolchains.

---

## 12. Examples, case studies, and proof obligations

Source intent:

- `docs/future/impls/11_case_study_warp_specialization_pipelining.md`
- `docs/future/story.md`
- `docs/future/reports/retargetable_extensibility_report.md`

Checklist:

- `[ ]` Turn warp specialization into a real staged pass sequence with tests and
  artifact examples.
- `[ ]` Turn software pipelining into a real staged pass sequence with tests and
  artifact examples.
- `[ ]` Add CSP/process/channel example programs that exercise protocol typing.
- `[ ]` Add serving-routine examples above the current kernel-level examples.
- `[ ]` Add extension-composition examples showing solver-visible pipeline
  choice.
- `[ ]` Keep `docs/design/` and `docs/future/` synchronized as features land so
  the narrative stays honest.

---

## 13. Process / repo discipline gaps

These are not compiler-architecture gaps, but they are required to keep future
work healthy.

- `[~]` The repo policy now states that `htp/dev` must stay stable and that new
  features should land via `htp/feat-*` branches and PR review.
- `[ ]` Enforce that branch policy in contributor workflow and automation, not
  only prose guidance.
- `[ ]` Keep this checklist current whenever a future item lands in code.
- `[ ]` When an item is implemented, move the normative doc from `docs/future/`
  to `docs/design/` and add code references there.

---

## 14. Recommended tracking order

If future work resumes now, the least-risk order is:

1. solver evolution
2. agent-loop productization
3. semantic breadth
4. MLIR round-trip broadening
5. AIE toolchain execution
6. next backend / next programming model surface

That order matches the current architecture risk: composition drift is the next
real threat, not lack of one more backend stub.
