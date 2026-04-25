# TODO

`docs/todo/` tracks feature-sized gaps that are not implemented yet.

## Current Gaps

- [x] Agent harness scaffold
- [x] Compiler story and architecture design (`docs/design/compiler_framework.md`)
- [x] Implementation-ready compiler design
- [x] Minimal package and verification tooling
- [x] First executable compiler slice
- [x] Strong self-running example showcase

## Future Showcase Cases

- [ ] `scf_while_state_machine`: demonstrate MLIR/xDSL-style SCF while
  before/after region contracts and execution evidence when current semantics
  can support the case.
- [ ] `affine_loop_nest_execution`: demonstrate nested affine loop execution
  and access legality after affine support goes beyond fact and lowering
  evidence.
- [ ] `vector_compute_pipeline`: demonstrate vector compute semantics and
  transformations after vector support goes beyond type/access-oriented facts.

Each future feature should have a clear input, output, and verification contract.
