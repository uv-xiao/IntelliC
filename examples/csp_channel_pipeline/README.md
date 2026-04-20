# CSP Channel Pipeline Example

This example exercises the CSP authoring surface on top of the shared HTP
pipeline.

It proves three implemented contracts:

- CSP process/channel metadata lowers into typed workload and effect state
  through nested `@p.process(...)` functions instead of direct dict assembly.
- the example now carries explicit `producer`, `router`, and `consumer`
  process roles plus structured protocol-local compute steps emitted via
  native-looking calls such as `packed = p.pack_tile(...)`.
- the workload uses `p.args.<name>` and default process argument capture so the
  flagship CSP example does not wire kernel arguments through raw string tuples.
- the pipeline is now decomposed into four named processes over three channels
  (`tiles`, `partials`, `ready_rows`) instead of a minimal three-process toy.
- balanced channel obligations and deadlock-safety evidence are recorded in
  staged `state.json#/aspects/effects`.
- process-local protocol steps remain visible in staged
  `state.json#/items/workload_ir`.
- replay can now execute channel send/recv through runtime-managed in-memory
  queues instead of turning those protocol steps into generic stub hits.

Run:

```bash
python -m examples.csp_channel_pipeline.demo
```
