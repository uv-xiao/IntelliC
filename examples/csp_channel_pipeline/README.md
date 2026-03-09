# CSP Channel Pipeline Example

This example exercises the CSP authoring surface on top of the shared HTP
pipeline.

It proves three implemented contracts:

- CSP process/channel metadata lowers into typed workload and effect state through a decorator/builder surface instead of direct dict assembly.
- the example can express a multi-channel dispatch/combine/writeback protocol with named processes and capacities,
- Balanced channel obligations are recorded in staged `effects.json`.
- The final package remains replayable in `sim`.

Run:

```bash
python -m examples.csp_channel_pipeline.demo
```
