# PyPTO-Inspired PTO Vector Add

This example is the concrete HTP counterpart of the small PyPTO / `pto-runtime`
vector-add flow:

- compile a simple tile kernel to PTO artifacts,
- replay the final Python stage in `sim`,
- build the PTO package through the binding adapter,
- run the package through `pto-runtime` in `a2a3sim` when the local
  reference runtime and host compilers are available.

Run it from the repo root:

```bash
python -m examples.pto_pypto_vector_add.demo
```

The example writes outputs under `artifacts/pto_pypto_vector_add/`.

Notes:

- replay is always available because HTP stages stay runnable in `sim`;
- build/run require the local `references/pto-runtime/` checkout and the host
  compilers that `pto-runtime` expects;
- the current v1 execution path is a real PTO smoke run over the
  `host_build_graph` ABI rather than a full tensor-marshaling demo.
