# LittleKernel (Zhihu) viewpoint — emitter-first “retargeting”

This note captures (paraphrases) a specific viewpoint about “retargetable compilers” that emphasizes **emitter-first**
design and minimizing IR/passes.

Primary article (Chinese):
- https://zhuanlan.zhihu.com/p/2005441887369192285

Local copy used during research (gitignored, not committed):
- `references/size-littlekernel.md`

## Summary of claims (paraphrased)

- **“Python AST is the IR.”** Prefer staying in Python and keeping compilation lightweight.
- **Minimize passes.** Do only the indispensable ones (examples given: const-folding, inlining, type inference). Many other
  “compiler passes” are treated as optional or as simple AST transforms.
- **Emitter-first.** Put the “real work” into code emission; treat optimization as the process of producing the right
  low-level code shape.
- **Hot-pluggable intrinsics.** Hardware-specific features should be introduced as intrinsics (or attributes) and handled
  by emission rules rather than by deep, multi-layer IR rewrites.
- **Retargeting worldview.** With hardware fragmenting, there is no single unified low-level model; therefore retargeting
  should often mean “swap the emitter + register new intrinsics”, not “build a giant universal IR”.

## Why this matters for HTP

This viewpoint is valuable as a pressure-test:
- If HTP becomes “too MLIR-like” (too many passes, too much implicit invariants), it risks losing iteration speed and
  kernel-author productivity.

But it also highlights a gap HTP must close:
- For multi-target correctness and composability, HTP still needs **explicit semantic contracts** (capabilities/effects,
  layout rules, artifact manifests) so that “extensions” compose safely without relying on emitter-side tribal knowledge.

