# HTP Design Acceptance Checklist (Phase 8)

This checklist defines what it means for `docs/design/` to be “complete enough to implement”.

The intent is to eliminate hidden invariants: every extension point and semantic dependency must have a declared contract.

---

## 1) Readability and “full story”

- A new contributor can read in order:
  - `docs/design/README.md`
  - `docs/design/story.md`
  - `docs/design/analysis.md`
  - `docs/design/features.md`
  - `docs/design/implementations.md`
  - `docs/design/examples.md`
  and understand:
  - user-facing surfaces (kernels/WSP/CSP/routines),
  - compiler transforms (passes/pipelines),
  - backend/binding surfaces,
  - and emitted artifacts (file tree + manifest).

---

## 2) Semantic contracts are explicit

- Types are defined and shared (no “dialect-only parallel type universes”).
- Layout is a facet product model (distribution ⊗ memory ⊗ hardware), with:
  - legality predicates,
  - explicit relayout operations,
  - and “no silent conversion” as a rule.
- Effects/protocol obligations are explicit and dischargeable:
  - channels,
  - async tokens,
  - barriers,
  - collectives.

---

## 3) Extension points are contracted

Every extension unit has declared:

- identity + version
- `requires/provides/invalidates` capabilities
- diagnostics codes + payload schema
- artifact IO expectations (what it consumes/emits)

Extension units include:

- dialect packages (CoreKernel/WSP/CSP, plus others)
- intrinsic sets and `IntrinsicDecl` contracts
- passes (`PassContract`)
- pipeline templates (including final artifact contract requirements)
- backends (capabilities + artifact contracts + handler tables)
- bindings (validate/build/load/run/replay)
- MLIR round-trip islands (matcher/exporter/MLIR pipeline/importer + artifact contract)
- external toolchain integrations (artifact emission + toolchain contract)

Additionally:

- Pass contracts explicitly distinguish **AST mutation** vs **analysis production** (and record both in stage artifacts and
  `ir/pass_trace.jsonl`).

---

## 4) Artifact contract is complete and replayable

- `manifest.json` schema includes:
  - inputs, target, pipeline, capabilities
  - stage graph index
  - outputs index
  - replay metadata (`sim|device` modes)
- `ir/pass_trace.jsonl` is defined and points to stage dumps.
- Each stage directory has deterministic dumps:
  - `program.pyast.json` and `types/layout/effects/schedule` metadata
  - `ids/entities.json` and `ids/bindings.json` to index constructs/variables robustly
  - `analysis/index.json` plus serialized analysis results when passes produce analyses
  - `program.py` always exists and is runnable in `mode="sim"` (may be stubbed with explicit diagnostics)
  - `replay/stubs.json` exists whenever a stage is marked `stubbed`

---

## 5) Backend contracts are testable

For PTO:

- `codegen/pto/kernel_config.py` contract is specified and sufficient for binding integration (via existing runners such
  as PyPTO/Simpler-style `CodeRunner`).
- toolchain/runtime pins are recorded under `extensions.pto.*`.
- the binding-to-`pto-runtime` adapter boundary is specified for both `a2a3sim` and `a2a3`.

For NV-GPU:

- `codegen/nvgpu/` file contract is specified.
- Ampere and Blackwell are specified as profiles of one backend, not separate compiler stacks.
- toolchain/runtime pins are recorded under `extensions.nvgpu.*`.
- `.cu` is explicitly authoritative, while `nvcc`/`nvrtc`/loader policy is specified as binding-owned execution logic.

For optional extension backends/toolchains such as AIE:

- AIE backend MLIR artifact emission contract is specified.
- `codegen/aie/` file set is specified (`aie.mlir` + sidecars).
- toolchain/runtime pins are recorded under `extensions.aie.*`.

---

## 6) Debuggability is by construction

- Every failure mode has a named diagnostic code family:
  - capability mismatches
  - layout incompatibilities
  - effect/protocol violations
  - missing handler / backend gaps
- Diagnostics always include `node_id`, structured payload pointer, and structured fix-hint pointer.
- Stage-to-stage “semantic diff” is possible from dumps (stable ordering + ids).

---

## 7) Testing strategy exists (even before code)

- Golden artifact tests are described (what to compare and why).
- Diagnostic stability tests are described (assert codes/payload, not messages).
- Contract validators are described for backends and replay.

---

## 8) Agent-native development is a first-class target

- The design explicitly treats LLM-based development as a native target (not “optional future tooling”):
  - replayable stages in `sim` are non-negotiable
  - diagnostics and manifests are machine-consumable by default (stable codes + structured payloads)
  - staged analyses exist for any fact that justifies a transform
  - provenance for autonomous edits is specified (`extensions.agent.*`)
- There is a clear agent loop/tooling story that consumes only artifacts and produces auditable evidence:
  - `docs/design/feats/10_agentic_development.md`
  - `docs/design/impls/10_agentic_tooling.md`

---

## 9) MLIR round-trip island scope is pinned

- The design defines a normative v1 eligible subset for MLIR round-trip islands.
- The design defines the normative v1 exporter/importer statement and intrinsic subset for MLIR round-trip islands.
- The design defines a normative `ledger.json` role in export/import.
- The design defines how entity/binding identities survive MLIR rewrites and where rewrite maps are emitted.

---

## 10) Runtime and schema closure are pinned

- The design defines the normative v1 replay module surface (`STAGE_INFO`, `run(...)`).
- The design defines the normative v1 `htp.runtime` shim surface.
- The design defines the normative v1 `PassContract` minimum schema.
- The design defines the normative v1 `manifest.json` and per-stage record invariants.
- The design defines the normative v1 binding API and result record shapes.

---

## 11) V1 proof scope is pinned

- V1 is explicitly an end-to-end proof on both PTO and NV-GPU.
- The mandatory pass spine is explicit: `ast_canonicalize`, `typecheck_layout_effects`, staged analysis pass(es),
  `apply_schedule`, backend lowering, and package emission.
- MLIR-based round-trips are extensions; the core compiler only provides the extension mechanism.
- The examples document covers kernel/backend, CSP pipeline, optional extension backend, multi-backend serving, compiler
  extension, and staged warp-specialization-style optimization stories.
