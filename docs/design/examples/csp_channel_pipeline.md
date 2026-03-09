# CSP Channel Pipeline

Files:

- `examples/patterns/csp/channel_pipeline/demo.py`
- `examples/patterns/csp/channel_pipeline/README.md`

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
- The authored Python exposes a semantically meaningful three-stage affine
  pipeline:
  - `load_norm`
  - `project`
  - `writeback`
  with channels:
  - `input_tiles`
  - `hidden_tiles`
  - `completions`

Semantics:

- `load_norm` consumes activations and writes normalized hidden tiles
- `project` consumes both the input and hidden handoff streams, produces
  projected tiles, and signals completion
- `writeback` drains the completion stream into the final output

This is intentionally closer to a streaming neural-network block than to a
toy “prefetch / compute / epilogue” label set.
