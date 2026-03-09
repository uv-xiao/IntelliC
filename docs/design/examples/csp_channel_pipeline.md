# CSP Channel Pipeline

Files:

- `examples/csp_channel_pipeline/demo.py`
- `examples/csp_channel_pipeline/README.md`

This example uses the implemented `htp.csp` authoring surface to compile a
three-process channel pipeline with typed FIFO channels.

What it proves:

- CSP process/channel metadata lowers into the shared workload semantic model.
- The type/layout/effect pass emits balanced protocol obligations into staged
  `effects.json`.
- The final package remains replayable in `sim`.
- The public example can now be written through traced `@kernel` and
  `@csp.program(...)` surfaces plus `fifo(...)`, `put(...)`, `get(...)`, and
  `process(...)` helpers instead of inline nested dict payloads.
- The authored Python now exposes `prefetch`, `compute`, and `epilogue`
  processes plus the `tiles`, `partials`, and `completions` channels directly.
