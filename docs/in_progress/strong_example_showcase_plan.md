# Strong Example Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add challenging standalone IntelliC examples that demonstrate parse/print, semantic execution where currently supported, action evidence, and documented gaps.

**Architecture:** Keep examples as ordinary Python modules under `examples/`, each with a builder API, a `run_demo()` API for tests, and a `main()` for standalone execution. Share only small reporting helpers in `examples/common.py`; tests import example APIs directly and do not use an aggregate runner.

**Tech Stack:** Python 3.10 standard library, `unittest`, existing IntelliC dialect/syntax/semantic/action APIs, local xDSL/MLIR references for example inspiration only.

---

## File Structure

- Create `examples/common.py`
  - Owns shared `ExampleRun` evidence and `print_example_run()` formatting.
  - Does not discover or run examples collectively.
- Create `examples/scf_piecewise_accumulate.py`
  - Builds nested `scf.if` inside `scf.for` with current structural APIs.
  - Records parse/print and branch reachability evidence.
  - Documents `scf.if` concrete execution as an unsupported current capability.
- Create `examples/affine_stencil_tile.py`
  - Builds a richer affine scalar/vector memory-access module.
  - Records affine access, memory-effect, and lowering evidence.
  - Documents affine concrete memory execution as out of scope.
- Create `examples/action_cleanup_pipeline.py`
  - Builds an executable function/module with duplicate expressions, add-zero,
    a direct call, and dead private symbol.
  - Runs current passes and `MutatorStage`, then verifies semantic equivalence.
- Modify `tests/test_examples.py`
  - Keep existing example coverage where useful.
  - Add direct API tests for the three new examples.
- Modify `docs/in_progress/strong_example_showcase.md`
  - Mark implemented cases as `implemented` after tests pass.
  - Add verification evidence.

## Implementation Rules

- Use TDD for every new example: write a failing test first, run it, implement,
  then rerun focused tests.
- Do not implement missing compiler capabilities in this PR.
- If an example exposes an unsupported capability, record it in
  `ExampleRun.documented_gaps` and in the backlog notes.
- Keep each example runnable with `python -m examples.<module>`.
- Do not add `examples/__main__.py` or any aggregate example runner.

### Task 1: Shared Example Evidence Contract

**Files:**
- Create: `examples/common.py`
- Modify: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**

Add these imports and test case to `tests/test_examples.py`:

```python
from examples.common import ExampleRun, print_example_run
```

```python
class ExampleCommonTests(unittest.TestCase):
    def test_example_run_records_structured_evidence_and_prints_sections(self) -> None:
        run = ExampleRun(
            name="demo",
            canonical_ir='"demo.op"() : () -> ()',
            parse_print_idempotent=True,
            semantic_result=(5,),
            action_names=("verify-structure",),
            relation_counts={"ActionRun": 1},
            mutation_applied_count=0,
            documented_gaps=("no gap",),
        )

        text = print_example_run(run)

        self.assertIn("== demo ==", text)
        self.assertIn("parse_print_idempotent: true", text)
        self.assertIn("semantic_result: (5,)", text)
        self.assertIn("actions: verify-structure", text)
        self.assertIn("ActionRun: 1", text)
        self.assertIn("documented_gaps:", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_examples.ExampleCommonTests
```

Expected: fail with `ModuleNotFoundError: No module named 'examples.common'`.

- [ ] **Step 3: Implement the shared evidence helper**

Create `examples/common.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ExampleRun:
    name: str
    canonical_ir: str
    parse_print_idempotent: bool
    semantic_result: tuple[object, ...] | None = None
    semantic_records: Mapping[str, int] = field(default_factory=dict)
    action_names: tuple[str, ...] = ()
    relation_counts: Mapping[str, int] = field(default_factory=dict)
    mutation_applied_count: int = 0
    mutation_rejected_count: int = 0
    final_ir: str | None = None
    documented_gaps: tuple[str, ...] = ()


def print_example_run(run: ExampleRun) -> str:
    lines = [
        f"== {run.name} ==",
        "",
        "canonical_ir:",
        run.canonical_ir,
        "",
        f"parse_print_idempotent: {str(run.parse_print_idempotent).lower()}",
    ]
    if run.semantic_result is not None:
        lines.append(f"semantic_result: {run.semantic_result}")
    if run.semantic_records:
        lines.append("semantic_records:")
        lines.extend(f"  {key}: {value}" for key, value in sorted(run.semantic_records.items()))
    if run.action_names:
        lines.append(f"actions: {', '.join(run.action_names)}")
    if run.relation_counts:
        lines.append("relation_counts:")
        lines.extend(f"  {key}: {value}" for key, value in sorted(run.relation_counts.items()))
    lines.append(f"mutation_applied_count: {run.mutation_applied_count}")
    lines.append(f"mutation_rejected_count: {run.mutation_rejected_count}")
    if run.final_ir is not None:
        lines.extend(("", "final_ir:", run.final_ir))
    if run.documented_gaps:
        lines.append("documented_gaps:")
        lines.extend(f"  - {gap}" for gap in run.documented_gaps)
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.test_examples.ExampleCommonTests
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add examples/common.py tests/test_examples.py
git commit -m "test: add shared example evidence contract"
```

### Task 2: SCF Piecewise Accumulate Example

**Files:**
- Create: `examples/scf_piecewise_accumulate.py`
- Modify: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**

Add this import:

```python
from examples.scf_piecewise_accumulate import run_demo as run_scf_piecewise_demo
```

Add this test:

```python
class StrongExampleTests(unittest.TestCase):
    def test_scf_piecewise_accumulate_roundtrips_and_documents_if_execution_gap(self) -> None:
        run = run_scf_piecewise_demo()

        self.assertTrue(run.parse_print_idempotent)
        self.assertIn('"scf.if"', run.canonical_ir)
        self.assertIn('"scf.for"', run.canonical_ir)
        self.assertIn("sparse-constant-propagation", run.action_names)
        self.assertGreaterEqual(run.relation_counts["BranchReachability"], 1)
        self.assertIn("scf.if concrete execution is not implemented", run.documented_gaps)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_examples.StrongExampleTests.test_scf_piecewise_accumulate_roundtrips_and_documents_if_execution_gap
```

Expected: fail with `ModuleNotFoundError: No module named 'examples.scf_piecewise_accumulate'`.

- [ ] **Step 3: Implement the example**

Create `examples/scf_piecewise_accumulate.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from examples.common import ExampleRun, print_example_run
from intellic.actions import passes
from intellic.dialects import arith as arith_dialect, scf as scf_dialect
from intellic.ir.actions import PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import Block, Builder, Region, i1, i32, index, verify_operation
from intellic.ir.syntax.printer import print_operation
from intellic.surfaces.api import arith, builders, func, scf


@dataclass(frozen=True)
class ScfPiecewiseAccumulateExample:
    operation: object


def build_example() -> ScfPiecewiseAccumulateExample:
    @func.ir_function
    def scf_piecewise_accumulate(n: index) -> i32:
        zero_i = arith.constant(0, index)
        one_i = arith.constant(1, index)
        zero = arith.constant(0, i32)

        with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
            iv, total = loop.arguments
            cond = arith.constant(1, i1)
            iv_i32 = arith.index_cast(iv, i32)

            then_block = Block()
            then_region = Region.from_block_list([then_block])
            with Builder().insert_at_end(then_block) as builder:
                updated = builder.insert(arith_dialect.addi(total, iv_i32))
                builder.insert(scf_dialect.yield_(updated.results[0]))

            else_block = Block()
            else_region = Region.from_block_list([else_block])
            with Builder().insert_at_end(else_block) as builder:
                builder.insert(scf_dialect.yield_(total))

            if_op = builders.emit(
                scf_dialect.if_(
                    cond,
                    then_region=then_region,
                    else_region=else_region,
                    result_types=(i32,),
                ),
                "builder:scf.if",
            )
            scf.yield_(if_op.results[0])

        return loop.results[0]

    return ScfPiecewiseAccumulateExample(operation=scf_piecewise_accumulate.operation)


def run_demo() -> ExampleRun:
    example = build_example()
    verify_operation(example.operation)
    canonical_ir = print_operation(example.operation)
    parse_print_idempotent = canonical_ir == print_operation(parse_operation(canonical_ir))

    run = PipelineRun(example.operation)
    for action in (
        passes.verify_structure(),
        passes.sparse_constant_propagation(),
        passes.loop_invariant_code_motion(),
    ):
        action.run(run)

    return ExampleRun(
        name="scf_piecewise_accumulate",
        canonical_ir=canonical_ir,
        parse_print_idempotent=parse_print_idempotent,
        action_names=tuple(record.value["name"] for record in run.db.query("ActionRun")),
        relation_counts={
            "BranchReachability": len(run.db.query("BranchReachability")),
            "LoopInvariantCandidate": len(run.db.query("LoopInvariantCandidate")),
        },
        documented_gaps=("scf.if concrete execution is not implemented",),
    )


def main() -> None:
    print(print_example_run(run_demo()), end="")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.test_examples.StrongExampleTests.test_scf_piecewise_accumulate_roundtrips_and_documents_if_execution_gap
python -m examples.scf_piecewise_accumulate
```

Expected: both commands exit 0; module output includes `canonical_ir:`,
`parse_print_idempotent: true`, and `documented_gaps:`.

- [ ] **Step 5: Commit**

Run:

```bash
git add examples/scf_piecewise_accumulate.py tests/test_examples.py
git commit -m "feat: add standalone scf showcase example"
```

### Task 3: Affine Stencil Tile Example

**Files:**
- Create: `examples/affine_stencil_tile.py`
- Modify: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**

Add this import:

```python
from examples.affine_stencil_tile import run_demo as run_affine_stencil_demo
```

Add this test:

```python
    def test_affine_stencil_tile_records_accesses_and_lowering_evidence(self) -> None:
        run = run_affine_stencil_demo()

        self.assertTrue(run.parse_print_idempotent)
        self.assertIn('"affine.vector_load"', run.canonical_ir)
        self.assertIn('"affine.vector_store"', run.canonical_ir)
        self.assertIn("lower-affine-to-scf", run.action_names)
        self.assertGreaterEqual(run.relation_counts["AffineAccess"], 6)
        self.assertGreaterEqual(run.relation_counts["MemoryEffect"], 6)
        self.assertGreaterEqual(run.relation_counts["AffineExpansion"], 6)
        self.assertIn("affine concrete memory execution is not implemented", run.documented_gaps)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_examples.StrongExampleTests.test_affine_stencil_tile_records_accesses_and_lowering_evidence
```

Expected: fail with `ModuleNotFoundError: No module named 'examples.affine_stencil_tile'`.

- [ ] **Step 3: Implement the example**

Create `examples/affine_stencil_tile.py` using the existing affine builders:

```python
from __future__ import annotations

from dataclasses import dataclass

from examples.common import ExampleRun, print_example_run
from intellic.actions import passes
from intellic.dialects import affine, arith as arith_dialect, builtin
from intellic.dialects.memref import MemRefType
from intellic.dialects.vector import VectorType
from intellic.ir.actions import PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import Block, Builder, Region, i32, index, verify_operation
from intellic.ir.syntax.printer import print_operation


@dataclass(frozen=True)
class AffineStencilTileExample:
    module: object


def build_example() -> AffineStencilTileExample:
    memref_type = MemRefType(element_type=i32, shape=(None, None))
    vector_type = VectorType(element_type=i32, shape=(4,))
    block = Block(arg_types=(memref_type, index, index, index, index))
    memref, row, column, tile, width = block.arguments
    module = builtin.module(Region.from_block_list([block]))

    center = affine.AffineMap(2, 2, ("d0 + s0", "d1"))
    west = affine.AffineMap(2, 2, ("d0 + s0", "d1 - 1"))
    east = affine.AffineMap(2, 2, ("d0 + s0", "d1 + 1"))
    clamp = affine.AffineMap(2, 2, ("d0 + s0", "s1"))

    with Builder().insert_at_end(block) as builder:
        builder.insert(affine.min(clamp, dims=(row, column), symbols=(tile, width)))
        builder.insert(affine.max(clamp, dims=(row, column), symbols=(tile, width)))
        west_load = builder.insert(affine.load(memref, west, dims=(row, column), symbols=(tile, width)))
        center_load = builder.insert(affine.load(memref, center, dims=(row, column), symbols=(tile, width)))
        east_load = builder.insert(affine.load(memref, east, dims=(row, column), symbols=(tile, width)))
        summed = builder.insert(arith_dialect.addi(west_load.results[0], center_load.results[0]))
        builder.insert(affine.store(summed.results[0], memref, center, dims=(row, column), symbols=(tile, width)))
        vector_load = builder.insert(
            affine.vector_load(memref, center, dims=(row, column), symbols=(tile, width), vector_type=vector_type)
        )
        builder.insert(affine.vector_store(vector_load.results[0], memref, east, dims=(row, column), symbols=(tile, width)))
        builder.insert(affine.store(east_load.results[0], memref, west, dims=(row, column), symbols=(tile, width)))

    return AffineStencilTileExample(module=module)


def run_demo() -> ExampleRun:
    example = build_example()
    verify_operation(example.module)
    canonical_ir = print_operation(example.module)
    parse_print_idempotent = canonical_ir == print_operation(parse_operation(canonical_ir))

    run = PipelineRun(example.module)
    for action in (
        passes.verify_structure(),
        passes.common_subexpression_elimination(),
        passes.lower_affine_to_scf(),
    ):
        action.run(run)

    return ExampleRun(
        name="affine_stencil_tile",
        canonical_ir=canonical_ir,
        parse_print_idempotent=parse_print_idempotent,
        action_names=tuple(record.value["name"] for record in run.db.query("ActionRun")),
        relation_counts={
            "AffineAccess": len(run.db.query("AffineAccess")),
            "MemoryEffect": len(run.db.query("MemoryEffect")),
            "AffineExpansion": len(run.db.query("AffineExpansion")),
            "CSEMemoryEffect": len(run.db.query("CSEMemoryEffect")),
        },
        documented_gaps=("affine concrete memory execution is not implemented",),
    )


def main() -> None:
    print(print_example_run(run_demo()), end="")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.test_examples.StrongExampleTests.test_affine_stencil_tile_records_accesses_and_lowering_evidence
python -m examples.affine_stencil_tile
```

Expected: both commands exit 0; module output includes `AffineAccess`,
`MemoryEffect`, and the documented memory-execution gap.

- [ ] **Step 5: Commit**

Run:

```bash
git add examples/affine_stencil_tile.py tests/test_examples.py
git commit -m "feat: add affine stencil showcase example"
```

### Task 4: Action Cleanup Pipeline Example

**Files:**
- Create: `examples/action_cleanup_pipeline.py`
- Modify: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**

Add this import:

```python
from examples.action_cleanup_pipeline import run_demo as run_action_cleanup_demo
```

Add this test:

```python
    def test_action_cleanup_pipeline_runs_actions_and_preserves_semantics(self) -> None:
        run = run_action_cleanup_demo()

        self.assertTrue(run.parse_print_idempotent)
        self.assertEqual(run.semantic_result, (5,))
        self.assertIn("canonicalize-greedy", run.action_names)
        self.assertIn("common-subexpression-elimination", run.action_names)
        self.assertIn("symbol-dce-and-dead-code", run.action_names)
        self.assertIn("inline-single-call", run.action_names)
        self.assertGreaterEqual(run.relation_counts["MutationApplied"], 3)
        self.assertGreaterEqual(run.mutation_applied_count, 3)
        self.assertIsNotNone(run.final_ir)
        self.assertNotIn('"func.call"', run.final_ir)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_examples.StrongExampleTests.test_action_cleanup_pipeline_runs_actions_and_preserves_semantics
```

Expected: fail with `ModuleNotFoundError: No module named 'examples.action_cleanup_pipeline'`.

- [ ] **Step 3: Implement the example**

Create `examples/action_cleanup_pipeline.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from examples.common import ExampleRun, print_example_run
from intellic.actions import passes
from intellic.dialects import arith, builtin, func
from intellic.ir.actions import MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.semantics import TraceDB, execute_function
from intellic.ir.syntax import Block, Builder, Region, i32, verify_operation
from intellic.ir.syntax.printer import print_operation


@dataclass(frozen=True)
class ActionCleanupPipelineExample:
    module: object
    main: object


def build_example() -> ActionCleanupPipelineExample:
    module_block = Block()
    module = builtin.module(Region.from_block_list([module_block]))
    identity_type = func.FunctionType(inputs=(i32,), results=(i32,))

    identity_block = Block(arg_types=(i32,))
    with Builder().insert_at_end(identity_block) as builder:
        builder.insert(func.return_(identity_block.arguments[0]))
    identity = func.func("identity", identity_type, Region.from_block_list([identity_block]))
    identity.properties["sym_visibility"] = "private"

    dead_block = Block(arg_types=(i32,))
    with Builder().insert_at_end(dead_block) as builder:
        builder.insert(func.return_(dead_block.arguments[0]))
    dead = func.func("dead_private", identity_type, Region.from_block_list([dead_block]))
    dead.properties["sym_visibility"] = "private"

    main_block = Block(arg_types=(i32,))
    with Builder().insert_at_end(main_block) as builder:
        call = builder.insert(func.call("identity", (main_block.arguments[0],), identity_type))
        zero = builder.insert(arith.constant(0, i32))
        add_zero = builder.insert(arith.addi(call.results[0], zero.results[0]))
        one = builder.insert(arith.constant(1, i32))
        duplicate_one = builder.insert(arith.constant(1, i32))
        result = builder.insert(arith.addi(add_zero.results[0], duplicate_one.results[0]))
        builder.insert(func.return_(result.results[0]))
    main = func.func("main", identity_type, Region.from_block_list([main_block]))

    with Builder().insert_at_end(module_block) as builder:
        builder.insert(identity)
        builder.insert(dead)
        builder.insert(main)

    return ActionCleanupPipelineExample(module=module, main=main)


def run_demo() -> ExampleRun:
    example = build_example()
    verify_operation(example.module)
    canonical_ir = print_operation(example.module)
    parse_print_idempotent = canonical_ir == print_operation(parse_operation(canonical_ir))

    before_db = TraceDB()
    before_result = execute_function(example.main, (4,), before_db)

    run = PipelineRun(example.module)
    for action in (
        passes.verify_structure(),
        passes.canonicalize_greedy(),
        passes.common_subexpression_elimination(),
        passes.sparse_constant_propagation(),
        passes.symbol_dce_and_dead_code(),
        passes.inline_single_call(),
    ):
        action.run(run)
    MutatorStage().run(run)
    PendingRecordGate().run(run)
    verify_operation(example.module)

    after_db = TraceDB()
    after_result = execute_function(example.main, (4,), after_db)
    if after_result != before_result:
        raise AssertionError(f"semantic result changed: {before_result} -> {after_result}")

    final_ir = print_operation(example.module)
    if final_ir != print_operation(parse_operation(final_ir)):
        raise AssertionError("final IR is not parse-print idempotent")

    return ExampleRun(
        name="action_cleanup_pipeline",
        canonical_ir=canonical_ir,
        parse_print_idempotent=parse_print_idempotent,
        semantic_result=after_result,
        semantic_records={
            "before_ValueConcrete": len(before_db.query("ValueConcrete")),
            "after_ValueConcrete": len(after_db.query("ValueConcrete")),
        },
        action_names=tuple(record.value["name"] for record in run.db.query("ActionRun")),
        relation_counts={
            "MutationApplied": len(run.db.query("MutationApplied")),
            "MutationRejected": len(run.db.query("MutationRejected")),
            "RewriteEvidence": len(run.db.query("RewriteEvidence")),
            "SymbolLiveness": len(run.db.query("SymbolLiveness")),
            "CallGraphEdge": len(run.db.query("CallGraphEdge")),
        },
        mutation_applied_count=len(run.db.query("MutationApplied")),
        mutation_rejected_count=len(run.db.query("MutationRejected")),
        final_ir=final_ir,
    )


def main() -> None:
    print(print_example_run(run_demo()), end="")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.test_examples.StrongExampleTests.test_action_cleanup_pipeline_runs_actions_and_preserves_semantics
python -m examples.action_cleanup_pipeline
```

Expected: both commands exit 0; module output includes `semantic_result: (5,)`,
`MutationApplied`, and a `final_ir:` section without `func.call`.

- [ ] **Step 5: Commit**

Run:

```bash
git add examples/action_cleanup_pipeline.py tests/test_examples.py
git commit -m "feat: add action cleanup showcase example"
```

### Task 5: Documentation, Backlog Status, and Full Verification

**Files:**
- Modify: `docs/in_progress/strong_example_showcase.md`
- Modify: PR body for #72 after pushing

- [ ] **Step 1: Update backlog statuses and evidence**

In `docs/in_progress/strong_example_showcase.md`, update the backlog table rows:

```markdown
| `scf_piecewise_accumulate` | xDSL/MLIR SCF `if`/`for` examples and interpreter tests | nested SCF, branch reachability, loop/action records, parse/print, documented semantic gap | implemented | `scf.if` concrete execution remains documented as a current gap. |
| `affine_stencil_tile` | xDSL affine dialect and lower-affine tests; MLIR affine memory-access idioms | affine maps, min/max, scalar/vector access facts, memory effects, lowering evidence | implemented | Concrete memory execution remains documented as a current gap. |
| `action_cleanup_pipeline` | xDSL rewrite/canonicalization examples and transform tests | canonicalization, CSE, SCCP-style facts, DCE, inline evidence, mutation evidence, semantic preservation | implemented | Uses only currently implemented action behavior. |
```

Add a verification section:

Add this verification section:

````markdown
## Implementation Verification

```bash
python -m unittest tests/test_examples.py
python -m unittest discover -s tests
python scripts/check_repo_harness.py
python -m examples.scf_piecewise_accumulate
python -m examples.affine_stencil_tile
python -m examples.action_cleanup_pipeline
```
````

After running commands, append the observed `Ran ... OK` and command success
evidence under the code block.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
python -m unittest tests/test_examples.py
python -m unittest discover -s tests
python scripts/check_repo_harness.py
python -m examples.scf_piecewise_accumulate
python -m examples.affine_stencil_tile
python -m examples.action_cleanup_pipeline
```

Expected:

- `tests/test_examples.py` passes.
- full `tests` discovery passes.
- harness policy passes.
- each example module exits 0 and prints its own demo sections.

- [ ] **Step 3: Commit docs and final test updates**

Run:

```bash
git add docs/in_progress/strong_example_showcase.md tests/test_examples.py examples
git commit -m "docs: record strong example verification"
```

- [ ] **Step 4: Push and update PR #72**

Run:

```bash
git push
```

Update the PR body to list:

- the three implemented examples;
- the current-feature-only boundary;
- the documented gaps;
- local verification commands and results;
- GitHub `repo-harness` status after checks complete.

- [ ] **Step 5: Final readiness check**

Run:

```bash
gh pr view 72 --json url,state,isDraft,mergeable,mergeStateStatus,statusCheckRollup
git status --short --branch
```

Expected:

- PR #72 is open and either draft or ready according to user direction.
- working tree is clean.
- GitHub checks are passing or still in progress with local verification already
  recorded.

## Self-Review

- Spec coverage: every approved requirement maps to a task: standalone runnable
  modules, tests that reuse APIs directly, no aggregate runner, current-feature
  boundary, xDSL/MLIR inspiration, appendable backlog, and documented gaps.
- Placeholder scan: no task depends on unspecified implementation work.
- Type consistency: the shared `ExampleRun` fields are used by every planned
  example and by `tests/test_examples.py`.
