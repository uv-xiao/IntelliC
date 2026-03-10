# CPU Reference Vector Add

This example shows the lightweight `cpu_ref` backend using the same native HTP `@kernel` authoring surface as the other backends.

What it demonstrates:
- authoring with `htp.kernel` and `store(...)`
- compiling to a backend-owned package under `codegen/cpu_ref/`
- replaying the latest stage in `sim`
- building the CPU reference runtime sidecar
- running the emitted package against NumPy buffers

Run it with:
- `python -m examples.extensions.cpu_ref_vector_add.demo`
