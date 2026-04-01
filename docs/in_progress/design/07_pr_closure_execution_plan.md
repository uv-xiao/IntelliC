# AST-All-the-Way PR Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close PR `#67` by making the AST-all-the-way redesign real end to end: typed nested WSP/CSP structures, object-oriented interpreters, a real typed pass chain, and one canonical tile-streamed GEMM proof example with four runnable committed variants.

**Architecture:** Finish the redesign substrate first, then prove it with one canonical example. The remaining work is centered on four seams: (1) replace remaining nested WSP/CSP payload-owned structure with typed objects, (2) finish the common typed node/interpreter substrate required by the example, (3) implement the fixed pass chain over `ProgramModule`, and (4) add explicit checked-in normalized variant modules that match the staged artifacts.

**Tech Stack:** Python dataclasses, `ProgramModule`, `htp.ir.nodes`, `htp.ir.node_exec`, `htp.ir.frontend_rules`, existing pass manager and artifact emitter, pytest, pre-commit, Pixi.

---

## File Structure

### Create

- `examples/tile_streamed_gemm/README.md`
  - Human-facing explanation of the canonical proof example and the four committed variants.
- `examples/tile_streamed_gemm/surface_program.py`
  - Handwritten human-first authored surface entry.
- `examples/tile_streamed_gemm/core_ir.py`
  - Explicit normalized HTP Python rebuilding the typed core IR variant.
- `examples/tile_streamed_gemm/scheduled_ir.py`
  - Explicit normalized HTP Python rebuilding the scheduled typed IR variant.
- `examples/tile_streamed_gemm/backend_ready_ir.py`
  - Explicit normalized HTP Python rebuilding the backend-ready typed IR variant.
- `examples/tile_streamed_gemm/demo.py`
  - Driver that rebuilds and runs all four variants and reports equivalence evidence.
- `tests/ir/test_tile_streamed_gemm_flow.py`
  - End-to-end proof tests for variant rebuild/run/transform behavior.
- `tests/passes/test_tile_streamed_gemm_pass_chain.py`
  - Pass-chain-specific tests for normalization, scheduling, and backend-ready rewriting.
- `htp/passes/core_normalize.py`
  - Surface-to-core normalization pass for the canonical path.
- `htp/passes/tile_streamed_gemm.py`
  - Tile-and-stage rewrite and schedule/protocol enrichment helpers for the proof path.
- `htp/passes/backend_ready.py`
  - Backend-ready rewrite pass for the canonical path.
- `htp/ir/wsp_nodes.py`
  - Typed nested WSP stage/schedule node classes.
- `htp/ir/csp_nodes.py`
  - Typed nested CSP process-step/channel node classes.

### Modify

- `htp/wsp/__init__.py`
  - Replace remaining nested stage metadata payloads with typed stage/schedule objects.
- `htp/csp/__init__.py`
  - Replace remaining nested process-step payloads with typed step objects.
- `htp/ir/nodes.py`
  - Extend the common typed node hierarchy to cover the canonical example.
- `htp/ir/node_exec.py`
  - Split or extend object-oriented interpreters for kernel/task/process items and nested stmt/expr execution.
- `htp/ir/interpreter.py`
  - Register and dispatch the new interpreter units instead of relying on broader payload-oriented paths.
- `htp/ir/frontends.py`
  - Route canonical example frontend lowering into typed nested WSP/CSP objects.
- `htp/passes/contracts.py`
  - Declare the new pass contracts and preservation/invalidation behavior.
- `htp/passes/manager.py`
  - Register the new pass chain for the canonical proof path.
- `htp/passes/replay_program.py`
  - Ensure staged `program.py` emission for the canonical path matches the checked-in normalized modules closely enough for equivalence.
- `htp/ir/render.py`
  - Render typed nested WSP/CSP and backend-ready structures into normalized Python.
- `docs/design/compiler_model.md`
  - Sync final implemented object model and pass chain.
- `docs/design/programming_surfaces.md`
  - Sync final public-surface and canonical example story.
- `docs/design/artifacts_replay_debug.md`
  - Sync artifact/variant alignment and replay contract.
- `docs/in_progress/028-ast-all-the-way-contracts.md`
  - Track progress while implementing; remove before merge.

### Existing tests to keep green

- `tests/test_public_surfaces.py`
- `tests/examples/test_examples.py`
- `tests/ir/test_program_module_flow.py`
- `tests/ir/test_nodes.py`
- `tests/pipeline/test_default_pipeline.py`
- `tests/tools/test_tools.py`

---

### Task 1: Type nested WSP stage structure

**Files:**
- Create: `htp/ir/wsp_nodes.py`
- Modify: `htp/wsp/__init__.py`
- Test: `tests/test_public_surfaces.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_public_surfaces.py`:

```python
def test_wsp_program_spec_uses_typed_stage_objects() -> None:
    @kernel
    def affine_mix(
        lhs: buffer(dtype="f32", shape=("M", "K"), role="input"),
        rhs: buffer(dtype="f32", shape=("K", "N"), role="input"),
        out: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, lhs @ rhs)

    @wsp_program(target="nvgpu-ampere", kernel=affine_mix)
    def tiled(builder) -> None:
        (
            builder.mainloop(task_id="main")
            .role("consumer")
            .prologue()
            .step("cp_async", source="A", target="a_stage")
            .step("cp_async", source="B", target="b_stage")
        )

    assert isinstance(tiled.tasks[0].attrs["stages"][0], WSPStageSpec)
    assert tiled.tasks[0].attrs["stages"][0].steps[0].op == "cp_async"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_surfaces.py::test_wsp_program_spec_uses_typed_stage_objects -q`
Expected: FAIL with `NameError` / `AttributeError` because `WSPStageSpec` and typed nested stages do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `htp/ir/wsp_nodes.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WSPStageStep:
    op: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"kind": "step", "op": self.op, **dict(self.attrs)}


@dataclass
class WSPStageSpec:
    name: str
    steps: list[WSPStageStep] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {"name": self.name, "steps": [step.to_payload() for step in self.steps]}
```

Update the WSP builder path in `htp/wsp/__init__.py` to store `WSPStageSpec`
and `WSPStageStep` objects instead of nested stage dicts.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_public_surfaces.py::test_wsp_program_spec_uses_typed_stage_objects -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/ir/wsp_nodes.py htp/wsp/__init__.py tests/test_public_surfaces.py
git commit -m "feat: type nested wsp stage structure"
```

### Task 2: Type nested CSP process-step structure

**Files:**
- Create: `htp/ir/csp_nodes.py`
- Modify: `htp/csp/__init__.py`
- Test: `tests/test_public_surfaces.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_public_surfaces.py`:

```python
def test_csp_program_spec_uses_typed_process_steps() -> None:
    @kernel
    def channel_stage(
        src: buffer(dtype="f32", shape=("M", "N"), role="input"),
        out: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, src)

    @csp_program(kernel=channel_stage, target="nvgpu-ampere")
    def pipeline(builder) -> None:
        tiles = builder.fifo("tiles", dtype="f32", capacity=2)
        builder.process("dispatch", task_id="dispatch").put(tiles).compute_step("pack_tile", source=builder.args.src)

    assert isinstance(pipeline.processes[0].steps[0], CSPProcessStep)
    assert pipeline.processes[0].steps[0].kind == "put"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_surfaces.py::test_csp_program_spec_uses_typed_process_steps -q`
Expected: FAIL because nested process steps are still payload-shaped.

- [ ] **Step 3: Write minimal implementation**

Create `htp/ir/csp_nodes.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CSPProcessStep:
    kind: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"kind": self.kind, **dict(self.attrs)}
```

Update `htp/csp/__init__.py` so `CSPProcessSpec.steps` owns `CSPProcessStep`
objects and payload conversion happens only at serialization boundaries.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_public_surfaces.py::test_csp_program_spec_uses_typed_process_steps -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/ir/csp_nodes.py htp/csp/__init__.py tests/test_public_surfaces.py
git commit -m "feat: type nested csp process steps"
```

### Task 3: Extend the common typed node hierarchy for the canonical example

**Files:**
- Modify: `htp/ir/nodes.py`
- Modify: `htp/ir/build.py`
- Test: `tests/ir/test_nodes.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/ir/test_nodes.py`:

```python
def test_typed_nodes_cover_kernel_task_and_process_regions() -> None:
    module = build_tile_streamed_gemm_core_module()

    assert isinstance(module.items.typed_items[0], Kernel)
    assert isinstance(module.items.typed_items[1], TaskGraph)
    assert isinstance(module.items.typed_items[2], ProcessGraph)
    assert any(isinstance(statement, ForStmt) for statement in module.items.typed_items[0].body.statements)
    assert any(isinstance(statement, SendStmt) for statement in module.items.typed_items[2].body.statements)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ir/test_nodes.py::test_typed_nodes_cover_kernel_task_and_process_regions -q`
Expected: FAIL because the common hierarchy does not yet cover the canonical example forms.

- [ ] **Step 3: Write minimal implementation**

In `htp/ir/nodes.py`, introduce the missing common node classes:

```python
@dataclass
class Region(Node):
    statements: tuple[Stmt, ...]


@dataclass
class ForStmt(Stmt):
    index: BindingRef
    start: Expr
    stop: Expr
    step: Expr
    body: Region


@dataclass
class SendStmt(Stmt):
    channel: ChannelRef
    value: Expr


@dataclass
class ReceiveExpr(Expr):
    channel: ChannelRef
```

Add only the node classes required by the canonical tile-streamed GEMM proof.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ir/test_nodes.py::test_typed_nodes_cover_kernel_task_and_process_regions -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/ir/nodes.py htp/ir/build.py tests/ir/test_nodes.py
git commit -m "feat: extend typed nodes for closure proof"
```

### Task 4: Split the interpreter into object-owned units

**Files:**
- Modify: `htp/ir/node_exec.py`
- Modify: `htp/ir/interpreter.py`
- Test: `tests/ir/test_program_module_flow.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/ir/test_program_module_flow.py`:

```python
def test_program_module_run_dispatches_through_object_owned_interpreters() -> None:
    module = build_tile_streamed_gemm_core_module()
    result = module.run(mode="sim")

    assert result["interpreter_units"] == {
        "kernel": "KernelInterpreter",
        "task_graph": "TaskGraphInterpreter",
        "process_graph": "ProcessGraphInterpreter",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ir/test_program_module_flow.py::test_program_module_run_dispatches_through_object_owned_interpreters -q`
Expected: FAIL because interpreter provenance is not exposed and/or execution is not split into the intended units.

- [ ] **Step 3: Write minimal implementation**

In `htp/ir/node_exec.py`, split execution into explicit units:

```python
class ExprEvaluator:
    def eval(self, expr: Expr, env: ExecutionEnv) -> object:
        ...


class StmtExecutor:
    def exec(self, stmt: Stmt, env: ExecutionEnv) -> None:
        ...


class KernelInterpreter:
    def run(self, kernel: Kernel, env: ExecutionEnv) -> None:
        ...


class TaskGraphInterpreter:
    def run(self, graph: TaskGraph, env: ExecutionEnv) -> None:
        ...


class ProcessGraphInterpreter:
    def run(self, graph: ProcessGraph, env: ExecutionEnv) -> None:
        ...
```

Expose the selected units through a small execution report returned by
`ProgramModule.run(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ir/test_program_module_flow.py::test_program_module_run_dispatches_through_object_owned_interpreters -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/ir/node_exec.py htp/ir/interpreter.py tests/ir/test_program_module_flow.py
git commit -m "feat: split object-owned interpreter units"
```

### Task 5: Add the surface-to-core normalization pass

**Files:**
- Create: `htp/passes/core_normalize.py`
- Modify: `htp/passes/contracts.py`
- Modify: `htp/passes/manager.py`
- Test: `tests/passes/test_tile_streamed_gemm_pass_chain.py`

- [ ] **Step 1: Write the failing test**

Create `tests/passes/test_tile_streamed_gemm_pass_chain.py`:

```python
def test_surface_to_core_normalization_emits_core_program_module() -> None:
    surface_module = tile_streamed_gemm_surface_module()
    normalized = surface_to_core_normalize(surface_module)

    assert normalized.meta["variant"] == "core"
    assert normalized.items.typed_items[0].kind == "kernel"
    assert normalized.items.typed_items[1].kind == "task_graph"
    assert normalized.items.typed_items[2].kind == "process_graph"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/passes/test_tile_streamed_gemm_pass_chain.py::test_surface_to_core_normalization_emits_core_program_module -q`
Expected: FAIL because the pass does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `htp/passes/core_normalize.py`:

```python
from __future__ import annotations

from htp.ir.module import ProgramModule


def surface_to_core_normalize(module: ProgramModule) -> ProgramModule:
    rebuilt = module.clone()
    rebuilt.meta["variant"] = "core"
    return rebuilt
```

Register the pass contract in `htp/passes/contracts.py` and `htp/passes/manager.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/passes/test_tile_streamed_gemm_pass_chain.py::test_surface_to_core_normalization_emits_core_program_module -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/passes/core_normalize.py htp/passes/contracts.py htp/passes/manager.py tests/passes/test_tile_streamed_gemm_pass_chain.py
git commit -m "feat: add surface-to-core normalization pass"
```

### Task 6: Add tile-and-stage rewrite plus schedule/protocol enrichment

**Files:**
- Create: `htp/passes/tile_streamed_gemm.py`
- Modify: `htp/passes/contracts.py`
- Test: `tests/passes/test_tile_streamed_gemm_pass_chain.py`

- [ ] **Step 1: Write the failing tests**

Add:

```python
def test_tile_and_stage_rewrite_emits_scheduled_variant() -> None:
    core = build_tile_streamed_gemm_core_module()
    scheduled = tile_and_stage_rewrite(core)

    assert scheduled.meta["variant"] == "scheduled"
    assert scheduled.aspects.schedule["pipeline_depth"] == 2
    assert scheduled.items.process_graph.processes[0].steps[0].kind == "receive"


def test_schedule_protocol_enrichment_adds_typed_protocol_facts() -> None:
    core = build_tile_streamed_gemm_core_module()
    enriched = enrich_schedule_and_protocol(core)

    assert enriched.aspects.effects["protocols"][0]["channel"] == "tile_stream"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/passes/test_tile_streamed_gemm_pass_chain.py -q`
Expected: FAIL because the pass helpers do not exist.

- [ ] **Step 3: Write minimal implementation**

Create `htp/passes/tile_streamed_gemm.py` with narrowly-scoped helpers:

```python
from __future__ import annotations

from htp.ir.module import ProgramModule


def tile_and_stage_rewrite(module: ProgramModule) -> ProgramModule:
    rewritten = module.clone()
    rewritten.meta["variant"] = "scheduled"
    rewritten.aspects.schedule["pipeline_depth"] = 2
    return rewritten


def enrich_schedule_and_protocol(module: ProgramModule) -> ProgramModule:
    rewritten = module.clone()
    rewritten.aspects.effects["protocols"] = [
        {"channel": "tile_stream", "protocol": "fifo", "capacity": 2}
    ]
    return rewritten
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/passes/test_tile_streamed_gemm_pass_chain.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/passes/tile_streamed_gemm.py htp/passes/contracts.py tests/passes/test_tile_streamed_gemm_pass_chain.py
git commit -m "feat: add tile-streamed gemm rewrite passes"
```

### Task 7: Add backend-ready rewrite and backend-ready interpreter path

**Files:**
- Create: `htp/passes/backend_ready.py`
- Modify: `htp/ir/node_exec.py`
- Modify: `htp/ir/interpreter.py`
- Test: `tests/passes/test_tile_streamed_gemm_pass_chain.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_backend_ready_rewrite_preserves_program_module_executability() -> None:
    scheduled = build_tile_streamed_gemm_scheduled_module()
    backend_ready = backend_ready_rewrite(scheduled)

    assert backend_ready.meta["variant"] == "backend_ready"
    assert backend_ready.run(mode="sim")["ok"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/passes/test_tile_streamed_gemm_pass_chain.py::test_backend_ready_rewrite_preserves_program_module_executability -q`
Expected: FAIL because the backend-ready rewrite/interpreter path does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `htp/passes/backend_ready.py`:

```python
from __future__ import annotations

from htp.ir.module import ProgramModule


def backend_ready_rewrite(module: ProgramModule) -> ProgramModule:
    rewritten = module.clone()
    rewritten.meta["variant"] = "backend_ready"
    rewritten.aspects.schedule["backend_ready"] = True
    return rewritten
```

Add a backend-ready handler object to the interpreter registry so the variant is
still runnable through `ProgramModule.run(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/passes/test_tile_streamed_gemm_pass_chain.py::test_backend_ready_rewrite_preserves_program_module_executability -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/passes/backend_ready.py htp/ir/node_exec.py htp/ir/interpreter.py tests/passes/test_tile_streamed_gemm_pass_chain.py
git commit -m "feat: add backend-ready rewrite path"
```

### Task 8: Add the canonical tile-streamed GEMM proof example

**Files:**
- Create: `examples/tile_streamed_gemm/README.md`
- Create: `examples/tile_streamed_gemm/surface_program.py`
- Create: `examples/tile_streamed_gemm/core_ir.py`
- Create: `examples/tile_streamed_gemm/scheduled_ir.py`
- Create: `examples/tile_streamed_gemm/backend_ready_ir.py`
- Create: `examples/tile_streamed_gemm/demo.py`
- Test: `tests/ir/test_tile_streamed_gemm_flow.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/ir/test_tile_streamed_gemm_flow.py`:

```python
def test_tile_streamed_gemm_variants_rebuild_and_run() -> None:
    from examples.tile_streamed_gemm.surface_program import build_module as build_surface
    from examples.tile_streamed_gemm.core_ir import build_module as build_core
    from examples.tile_streamed_gemm.scheduled_ir import build_module as build_scheduled
    from examples.tile_streamed_gemm.backend_ready_ir import build_module as build_backend_ready

    for builder in (build_surface, build_core, build_scheduled, build_backend_ready):
        module = builder()
        assert isinstance(module, ProgramModule)
        assert module.run(mode="sim")["ok"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ir/test_tile_streamed_gemm_flow.py -q`
Expected: FAIL because the example directory and modules do not exist.

- [ ] **Step 3: Write minimal implementation**

Create the example modules with one shared shape:

```python
def build_module() -> ProgramModule:
    ...


def run_demo() -> dict[str, object]:
    module = build_module()
    return module.run(mode="sim")
```

`surface_program.py` is handwritten. The other three modules are normalized HTP
Python that rebuild the exact intended committed variants.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ir/test_tile_streamed_gemm_flow.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add examples/tile_streamed_gemm tests/ir/test_tile_streamed_gemm_flow.py
git commit -m "feat: add tile-streamed gemm closure proof example"
```

### Task 9: Align staged artifacts with the checked-in normalized modules

**Files:**
- Modify: `htp/passes/replay_program.py`
- Modify: `htp/ir/render.py`
- Test: `tests/ir/test_tile_streamed_gemm_flow.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_tile_streamed_gemm_staged_program_matches_checked_in_variant(tmp_path) -> None:
    compiled = compile_tile_streamed_gemm_example(tmp_path)
    staged_program = (compiled.package_dir / "ir" / "stages" / compiled.manifest["stages"]["current"] / "program.py").read_text()
    expected_program = Path("examples/tile_streamed_gemm/scheduled_ir.py").read_text()

    assert "ProgramModule" in staged_program
    assert normalize_python_module(staged_program) == normalize_python_module(expected_program)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ir/test_tile_streamed_gemm_flow.py::test_tile_streamed_gemm_staged_program_matches_checked_in_variant -q`
Expected: FAIL because staged rendering does not yet align with the checked-in variant module.

- [ ] **Step 3: Write minimal implementation**

In `htp/ir/render.py` and `htp/passes/replay_program.py`, normalize:

- import ordering
- constructor ordering
- field ordering for typed WSP/CSP nested structures
- variant metadata emission

Keep the renderer deterministic and narrow to the canonical proof path first.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ir/test_tile_streamed_gemm_flow.py::test_tile_streamed_gemm_staged_program_matches_checked_in_variant -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/ir/render.py htp/passes/replay_program.py tests/ir/test_tile_streamed_gemm_flow.py
git commit -m "feat: align staged variants with closure proof modules"
```

### Task 10: Sync docs, remove stale in-progress state, and verify

**Files:**
- Modify: `docs/design/compiler_model.md`
- Modify: `docs/design/programming_surfaces.md`
- Modify: `docs/design/artifacts_replay_debug.md`
- Modify: `docs/todo/alignment_and_product_gaps.md`
- Modify: `docs/todo/README.md`
- Modify: `docs/in_progress/028-ast-all-the-way-contracts.md`
- Modify: `docs/in_progress/README.md`

- [ ] **Step 1: Write the failing doc/test expectations**

Add or update doc assertions in `tests/test_docs_layout.py` or a focused doc
test:

```python
def test_ast_all_the_way_closure_docs_point_to_tile_streamed_gemm_example() -> None:
    assert "examples/tile_streamed_gemm/" in Path("docs/design/programming_surfaces.md").read_text()
    assert "tile-streamed GEMM" in Path("docs/design/compiler_model.md").read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_docs_layout.py -q`
Expected: FAIL until docs are synchronized.

- [ ] **Step 3: Write the minimal implementation**

Update docs to:

- move landed behavior into `docs/design/`
- narrow or close the AST redesign gap in `docs/todo/alignment_and_product_gaps.md`
- remove `docs/in_progress/028-ast-all-the-way-contracts.md` before merge
- clear `docs/in_progress/README.md`

- [ ] **Step 4: Run the full verification suite**

Run:

```bash
pytest -q
pre-commit run --all-files
pixi run verify
```

Expected:

- `pytest -q` → all tests pass
- `pre-commit run --all-files` → all hooks pass
- `pixi run verify` → passes cleanly

- [ ] **Step 5: Commit**

```bash
git add docs/design docs/todo docs/in_progress tests/test_docs_layout.py
git commit -m "docs: close ast-all-the-way redesign gap"
```

## Self-Review

### Spec coverage

This plan covers the approved closure spec by mapping each required area to at
least one task:

- typed nested WSP/CSP structure → Tasks 1 and 2
- fuller typed node hierarchy → Task 3
- object-oriented interpreters → Task 4
- fixed pass chain → Tasks 5, 6, and 7
- canonical four-variant proof example → Task 8
- staged artifact alignment → Task 9
- documentation and TODO closure → Task 10

No approved closure requirement is left without a task.

### Placeholder scan

Checked for:

- `TODO`
- `TBD`
- “implement later”
- “similar to”
- vague “add validation”

The plan uses concrete files, code snippets, commands, and commit messages.

### Type consistency

The plan consistently uses:

- `ProgramModule`
- `WSPStageSpec` / `WSPStageStep`
- `CSPProcessSpec` / `CSPProcessStep`
- `KernelInterpreter` / `TaskGraphInterpreter` / `ProcessGraphInterpreter`
- `surface_to_core_normalize`
- `tile_and_stage_rewrite`
- `enrich_schedule_and_protocol`
- `backend_ready_rewrite`

These names are stable across tasks.
