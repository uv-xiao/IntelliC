# Reference: pto-runtime (for PTO-WSP v10)

This folder contains reference notes and design context about `pto-runtime`, which PTO-WSP v10 targets as its primary runtime
substrate for Ascend simulation and device execution.

Local repository clone (gitignored): `references/pto-runtime/`.

## Contents

- `docs/reference/pto_runtime/analysis.md` — high-level analysis notes of pto-runtime architecture and current state
- `docs/reference/pto_runtime/integration.md` — PTO-WSP ↔ pto-runtime integration notes (v10 direction)
- `docs/reference/pto_runtime/gaps.md` — explicit gaps / missing features PTO-WSP needs (semantics-honest checklist)
- `docs/reference/pto_runtime/task_buffer.md` — preview/reference: task-buffer direction for bounded execution and true backpressure

## How this relates to PTO‑WSP v10 docs (reference only)

The PTO‑WSP v10 reference docs in this branch live under `docs/reference/pto-wsp/v10/`.
The relevant interface checkpoint is `docs/reference/pto-wsp/v10/v10_pto_runtime_interface.md`.
