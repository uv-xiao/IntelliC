# CSP Token Dispatch Pipeline

This example exercises the traced CSP authoring surface on top of the shared
HTP pipeline.

Reference calibration:

- `references/triton-distributed-knowingnothing/python/little_kernel/design/flashcomm_dispatch.py`

This example now models a token-dispatch pipeline rather than a fake affine
stage chain. The authored Python describes four steps:

- `stage_hbm_tile`
- `route_peer_tile`
- `commit_remote_tile`
- `retire_delivery`

The channels are:

- `staged_tiles`
- `routed_tiles`
- `completion_tokens`

What it proves:

- CSP process/channel metadata lowers into typed workload and effect state.
- Balanced channel obligations are recorded in staged `effects.json`.
- The final package remains replayable in `sim`.
- The public program now communicates a real transport protocol:
  stage the tile, route it, commit it, and retire the delivery.

Kernel semantics:

- `dispatch_token_tile` is a tile-local dispatch step, not an arbitrary
  compute placeholder.
- each process runs the same primitive over different buffers and protocol
  stages, which matches the producer-consumer flavor of the LittleKernel
  reference more honestly than the previous affine example.

Run:

```bash
python -m examples.patterns.csp.channel_pipeline.demo
```
