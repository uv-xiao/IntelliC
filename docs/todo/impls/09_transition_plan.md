# Impl: Next-Phase Transition Plan

This design started as a documentation-first redo, but the repository now also
contains an active `htp/` implementation and runnable examples under
`examples/`.

The purpose of this document is now narrower: define the next implementation
transitions beyond the already-landed substrate and backend proof points.

---

## 1) Scope and non-goals

In scope:

- keeping the implementation aligned with the design contracts under `docs/design/`
- explicit backend artifact contracts
- explicit pass/pipeline contracts (including analysis vs transform effects)
- runnable examples and verification gates

Out of scope:

- preserving legacy PTO-WSP internals
- performance tuning beyond contract-proving examples

---

## 2) Next implementation sequencing (recommended)

The following work should now be done in the smallest verifiable slices:

1) **Capability solver landing**
   - validate the current default pipeline via explicit capability state
   - emit explainable unsat reports
2) **Agent-facing tooling**
   - add replay/verify/diff/explain surfaces
   - add structured provenance for autonomous runs
3) **Semantic breadth expansion**
   - broaden the kernel/workload/dataflow op set
   - strengthen channel/process semantics
4) **MLIR round-trip expansion**
   - move beyond the current narrow CSE path
   - make eligibility/export/import contracts testable
5) **Optional extension backends**
   - AIE / MLIR-AIE artifact emission and binding/toolchain contracts

This ordering is chosen to control the next risk: compositional drift as the
system grows beyond the current proof-of-architecture milestone.

---

## 3) Compatibility strategy

If older tools expect legacy layouts or entrypoints:

- preserve compatibility at the **artifact boundary** (emit `kernel_config.py` etc.),
- not by keeping old internal IRs/passes.

Rationale: preserving compatibility through artifacts keeps the compiler internally clean and makes extensions retargetable.

For the next phase, compatibility should remain artifact-boundary-only. Do not
reintroduce legacy internal APIs to accelerate feature work.

---

## 4) Risks to avoid in the next phase

- implementing backend-specific features as hidden pipeline branches instead of capability-gated passes
- letting analyses live in memory-only caches (creates irreproducible behavior and breaks agent loops)
- allowing passes to depend on implicit ordering rather than explicit `requires/provides/invalidates`
- treating the current default pipeline as if it were already a solved
  composition layer
- adding agent automation without emitting explicit provenance and policy inputs
