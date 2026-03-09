# Feature: Debuggability & Introspection (Future Remainder)

Implemented debug behavior now lives under `docs/design/impls/09_debuggability.md`.

Remaining future scope:

- make diagnostics consistently include rich source-level references
  (`node_id`, `entity_id`, payload refs, and fix-hint refs) across all compiler,
  binding, and extension surfaces
- deepen semantic diff from section-level structural evidence into node-aware
  contract deltas for layout/effect/protocol violations
- add explicit debug guidance for deeper future island backends and broader
  toolchain execution modes beyond the current PTO/NV-GPU/AIE surfaces
