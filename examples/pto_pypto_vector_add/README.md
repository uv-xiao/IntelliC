# PyPTO-Inspired PTO Vector Add

This example is the concrete HTP counterpart of the small PyPTO / `pto-runtime`
vector-add flow:

- compile a simple tile kernel to PTO artifacts,
- replay the final Python stage in `sim`,
- build the PTO package through the binding adapter,
- optionally run the package through `pto-runtime`.

Run it from the repo root:

```bash
python -m examples.pto_pypto_vector_add.demo
```

The example writes outputs under `artifacts/pto_pypto_vector_add/`.

Notes:

- replay is always available because HTP stages stay runnable in `sim`;
- build/run require the local `references/pto-runtime/` checkout and the host
  compilers that `pto-runtime` expects.
