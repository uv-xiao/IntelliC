# AIE Channel Pipeline

This example exercises the AIE extension path with a small channelized
producer-consumer program.

What it proves:

- the explicit CSP surface can feed the AIE extension emitter
- the package emits mapping and FIFO artifacts under `codegen/aie/`
- the binding can build and run the reference AIE package path

Run:

```bash
python -m examples.extensions.aie_channel_pipeline.demo
```

Artifacts are written under `artifacts/extensions/aie_channel_pipeline/`.
