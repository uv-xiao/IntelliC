# Impl: Warp Specialization + Software Pipelining

This document covers the implemented staged pass sequence for warp
specialization and software pipelining.

Code anchors:

- `htp/passes/analyze_warp_specialization.py`
- `htp/passes/apply_warp_specialization.py`
- `htp/passes/analyze_software_pipeline.py`
- `htp/passes/apply_software_pipeline.py`
- `htp/passes/program_model.py`
- `tests/pipeline/test_warp_pipeline_passes.py`

## Implemented pass sequence

The default pass spine now contains these schedule-specialization passes after
`apply_schedule`:

1. `htp::analyze_warp_specialization@1`
2. `htp::apply_warp_specialization@1`
3. `htp::analyze_software_pipeline@1`
4. `htp::apply_software_pipeline@1`

What they do today:

- `analyze_warp_specialization`
  - reads schedule directives and target profile
  - emits `analysis/warp_role_plan.json`
  - records producer/consumer role counts plus handoff metadata
- `apply_warp_specialization`
  - writes the selected role plan into staged `schedule.json`
  - keeps the stage replayable in `sim`
- `analyze_software_pipeline`
  - emits `analysis/pipeline_plan.json`
  - records depth, buffering mode, stage order, and steady-state slots
- `apply_software_pipeline`
  - writes the chosen pipeline plan into staged `schedule.json`
  - annotates `scheduled_ops` with `slot` and `pipeline_stage`

## Artifact evidence

For a WSP program with non-trivial schedule directives, the stage graph now
contains:

- `ir/stages/<id>/analysis/warp_role_plan.json`
- `ir/stages/<id>/analysis/pipeline_plan.json`
- final `ir/stages/<id>/schedule.json` with:
  - `specialization`
  - `software_pipeline`
  - `warp_role_plan`
  - `launch`

## Current boundary

What is implemented:

- staged analysis artifacts
- staged transform effects on schedule state
- tests that prove the passes run in the default pipeline
- runnable WSP example packages that expose the emitted plans

What is not implemented yet:

- async-copy retiming over real loop bodies
- loop-dependence analysis as a separate staged artifact
- target-specific discharge of the plans into backend-only primitives

Those remain future work under `docs/todo/`.
