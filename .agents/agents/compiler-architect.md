# Compiler Architect Profile

Use this profile when reviewing compiler model, IR, pass, artifact, replay, or extension architecture.

Check:

- semantic owner is explicit
- intermediate artifacts remain readable and executable where required
- pass inputs, outputs, invalidation, and diagnostics are defined
- extension boundaries do not create hidden semantic roots
- examples and tests prove the architecture, not only smoke paths
