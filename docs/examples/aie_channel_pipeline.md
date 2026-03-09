# AIE Channel Pipeline Example

Code anchor: `examples/aie_channel_pipeline/demo.py`

This example exercises the current AIE extension path with:

- CSP-style producer/consumer processes
- a typed FIFO channel contract
- explicit AIE mapping and FIFO sidecars under `codegen/aie/`
- stage analysis payloads for AIE mapping/FIFO planning

What it proves today:

- `compile_program(..., target="aie-xdna2-npu1")` emits a valid AIE package
- replay still runs from the staged Python program in `sim`
- AIE sidecars are derived from explicit plans instead of placeholder comments
- `build(mode="device")` materializes reference AIE toolchain outputs under
  `build/aie/`
- `load(mode="device").run(...)` goes through emitted `codegen/aie/host.py`
  plus the built host-runtime sidecar
