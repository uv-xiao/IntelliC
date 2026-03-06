# Impl: Transition Plan (docs-only in this redo)

This redo intentionally produces **design documents only** under `docs/design/`. No production code is migrated or kept
from the old PTO-WSP codebase on this branch.

The purpose of this document is to make the eventual implementation transition executable and low-risk by being explicit
about ordering, compatibility expectations, and verification gates.

---

## 1) Scope and non-goals (for the docs-only redo)

In scope:

- a complete “ready to implement” design under `docs/design/`
- explicit backend artifact contracts
- explicit pass/pipeline contracts (including analysis vs transform effects)
- acceptance checklist for design completeness

Out of scope:

- any real compiler implementation in this branch
- shipping toolchain integrations
- performance work

---

## 2) Future implementation sequencing (recommended)

When implementation begins (in a separate branch/repo state), do it in the smallest verifiable slices:

1) **Repository/module rename**
   - rename repository/module from `pto-wsp` to `htp`
   - remove legacy `pto_wsp` entrypoints (no deprecation shims in the new architecture)
2) **Artifact substrate first**
   - implement package emission (`manifest.json`, stage dumps, `pass_trace.jsonl`)
   - implement the binding interface skeleton that can validate + replay stages
3) **Core passes and solver**
   - implement pass contracts and pass manager
   - implement capability solver with explainable failures
4) **Backend-by-backend landing**
   - PTO backend artifact emission + simulation replay first (`a2a3sim`)
   - then device execution (`a2a3`)
   - AIE island backend later (requires more external tooling)
5) **Golden tests before feature growth**
   - for each added pass/backend, add a golden artifact test and contract validation tests

This ordering is chosen to maximize “early feedback and stable substrate” rather than “feature completeness first”.

---

## 3) Compatibility strategy (if legacy adoption is required)

If older tools expect legacy layouts or entrypoints:

- preserve compatibility at the **artifact boundary** (emit `kernel_config.py` etc.),
- not by keeping old internal IRs/passes.

Rationale: preserving compatibility through artifacts keeps the compiler internally clean and makes extensions retargetable.

---

## 4) Risks to avoid (lessons encoded in the design)

- implementing backend-specific features as hidden pipeline branches instead of capability-gated passes
- letting analyses live in memory-only caches (creates irreproducible behavior and breaks agent loops)
- allowing passes to depend on implicit ordering rather than explicit `requires/provides/invalidates`
