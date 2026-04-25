# IntelliC Examples

Each example is runnable as its own Python module and returns structured
evidence that tests can import directly. The examples are not wired through an
aggregate runner; collective coverage belongs in tests.

## `sum_to_n`

Run:

```bash
python -m examples.sum_to_n
```

Shows the executable baseline for the current compiler slice. It builds a
`func.func` with an `scf.for` loop, prints canonical IR, verifies parse/print
idempotence, performs semantic execution for `n = 5`, and reports semantic trace
counts plus action evidence from the pass pipeline.

## `scf_piecewise_accumulate`

Run:

```bash
python -m examples.scf_piecewise_accumulate
```

Shows richer SCF-shaped IR with nested `scf.if` operations inside an `scf.for`
loop. It demonstrates canonical IR printing, parse/print idempotence, branch
reachability facts, and action evidence. Concrete `scf.if` semantic execution
is documented as a current gap.

## `affine_stencil_tile`

Run:

```bash
python -m examples.affine_stencil_tile
```

Shows affine dialect evidence with `affine.min`, `affine.max`, scalar memory
accesses, vector memory accesses, memory-effect facts, and affine lowering
records. Concrete affine memory execution is documented as a current gap.

## `action_cleanup_pipeline`

Run:

```bash
python -m examples.action_cleanup_pipeline
```

Shows action and mutation behavior on deliberately optimizable IR. It reports
canonicalization, CSE, sparse-constant-propagation-style facts, DCE, inlining,
semantic execution before and after cleanup, mutation evidence, and final IR
cleanup counts.
