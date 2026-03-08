# CSP Channel Pipeline

Files:

- `examples/csp_channel_pipeline/demo.py`
- `examples/csp_channel_pipeline/README.md`

This example uses the implemented `htp.csp` authoring surface to compile a
two-process pipeline with a typed FIFO channel.

What it proves:

- CSP process/channel metadata lowers into the shared workload semantic model.
- The type/layout/effect pass emits balanced protocol obligations into staged
  `effects.json`.
- The final package remains replayable in `sim`.
