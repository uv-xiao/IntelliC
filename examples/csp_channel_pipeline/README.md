# CSP Channel Pipeline Example

This example exercises the CSP authoring surface on top of the shared HTP
pipeline.

It proves three implemented contracts:

- CSP process/channel metadata lowers into typed workload and effect state through a decorator/builder surface instead of direct dict assembly.
- the example now carries explicit `producer`, `router`, and `consumer`
  process roles plus named protocol-local compute steps.
- balanced channel obligations and deadlock-safety evidence are recorded in
  staged `effects.json`.
- process-local protocol steps remain visible in staged `workload_ir.json`.

Run:

```bash
python -m examples.csp_channel_pipeline.demo
```
