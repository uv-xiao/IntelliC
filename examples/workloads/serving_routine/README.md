# Serving Routine

This example exercises the workload-level routine surface above single-kernel
programs.

What it proves:

- traced `htp.routine.program(...)` can author a readable workload
- typed FIFO channels and explicit task dependencies survive into
  `workload_ir.json`
- replay stays available through the final package

Run:

```bash
python -m examples.workloads.serving_routine.demo
```

Artifacts are written under `artifacts/workloads/serving_routine/`.
