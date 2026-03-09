# CSP Channel Pipeline Example

This example exercises the traced CSP authoring surface on top of the shared
HTP pipeline.

It proves three implemented contracts:

- CSP process/channel metadata lowers into typed workload and effect state.
- Balanced channel obligations are recorded in staged `effects.json`.
- The final package remains replayable in `sim`.
- The authored Python exposes a real three-stage affine pipeline with named
  processes and channels instead of a top-level process payload list.

The stages are:

- `load_norm`
- `project`
- `writeback`

The channels are:

- `input_tiles`
- `hidden_tiles`
- `completions`

This is intentionally a meaningful streaming block, not a toy
`prefetch/compute/epilogue` label set.

Run:

```bash
python -m examples.patterns.csp.channel_pipeline.demo
```
