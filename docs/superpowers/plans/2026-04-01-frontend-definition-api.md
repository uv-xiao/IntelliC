# Frontend Definition API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current registry-plus-`to_program_module()` convention with a real node-first frontend-definition substrate that builtin frontends use to construct `ProgramModule` through registered rules instead of ad hoc per-surface builders.

**Architecture:** Add a dedicated frontend-definition layer under `htp/ir/` with explicit rule objects, build context, and a registry-backed `FrontendSpec` that can either call direct builders or execute frontend rules. Migrate `htp.kernel` first as the proving frontend, then route compiler ingress through the new registry path, and finally sync docs/tests so the design and code agree that a frontend-definition substrate now exists in code, not only in design notes.

**Tech Stack:** Python dataclasses, existing `ProgramModule` / `KernelIR` / `WorkloadIR` types, existing dialect registry, pytest, pre-commit, Pixi.

---

## File Structure

### New files

- `htp/ir/frontend_rules.py`
  - Own the node-first frontend-definition substrate.
  - Define `FrontendBuildContext`, `FrontendRule`, `FrontendRuleResult`, and helper constructors for common rule styles.
- `tests/ir/test_frontend_rules.py`
  - Prove the new substrate directly: rule execution, error handling, and `ProgramModule` construction.
- `docs/superpowers/plans/2026-04-01-frontend-definition-api.md`
  - This implementation plan.

### Modified files

- `htp/ir/frontends.py`
  - Extend `FrontendSpec` so a frontend can be defined either by a direct builder or by a rule object.
  - Make builtin frontend registration use the new API.
- `htp/compiler.py`
  - Keep compiler ingress registry-driven, but make it call the new `FrontendSpec.build(...)` entry instead of a raw callback.
- `htp/kernel.py`
  - Add the first node-first frontend-definition path for `KernelSpec`.
  - Keep `to_program_module()` as a delegating compatibility shim only inside this branch until the full PR is ready.
- `htp/routine.py`
  - After the kernel proof path lands, migrate routine ingress to the shared frontend-definition API if the substrate is already stable.
- `docs/in_progress/design/03_dialects_and_frontends.md`
  - Record the concrete frontend-rule API that actually shipped.
- `docs/in_progress/design/05_implementation_and_migration.md`
  - Update implementation status from “registry slice” to “rule-backed substrate”.
- `docs/in_progress/design/README.md`
  - Narrow the remaining frontend gap after the kernel proof path lands.
- `docs/in_progress/028-ast-all-the-way-contracts.md`
  - Track the frontend-definition milestone explicitly.
- `docs/design/programming_surfaces.md`
  - Describe implemented frontend ingress behavior with code pointers.
- `docs/design/compiler_model.md`
  - Describe how compiler ingress now reconstructs `ProgramModule` from registered frontend rules.

### Existing tests to update or keep green

- `tests/ir/test_frontends.py`
- `tests/ir/test_frontend.py`
- `tests/test_public_surfaces.py`
- `tests/compiler/test_compile_program.py`

---

### Task 1: Add direct failing tests for the frontend-rule substrate

**Files:**
- Create: `tests/ir/test_frontend_rules.py`
- Modify: `tests/ir/test_frontends.py`
- Test: `tests/ir/test_frontend_rules.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import pytest

from htp.ir.frontend_rules import FrontendBuildContext, FrontendRule, FrontendRuleResult
from htp.ir.frontends import FrontendSpec
from htp.ir.module import ProgramModule


class DemoSurface:
    def __init__(self, entry: str) -> None:
        self.entry = entry


def test_frontend_rule_builds_program_module() -> None:
    def build_demo(context: FrontendBuildContext) -> FrontendRuleResult:
        module = ProgramModule.from_program_dict(
            {
                "entry": context.surface.entry,
                "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": context.surface.entry}},
                "kernel_ir": {},
                "workload_ir": {},
            },
            meta={"source_surface": "demo.rule"},
        )
        return FrontendRuleResult(module=module)

    spec = FrontendSpec(
        frontend_id="demo.surface",
        dialect_id="htp.core",
        surface_type=DemoSurface,
        rule=FrontendRule(name="build_demo", build=build_demo),
    )

    module = spec.build(DemoSurface("demo_entry"))

    assert isinstance(module, ProgramModule)
    assert module.to_state_dict()["entry"] == "demo_entry"
    assert module.meta["source_surface"] == "demo.rule"


def test_frontend_rule_rejects_non_program_module_results() -> None:
    def bad_build(context: FrontendBuildContext) -> FrontendRuleResult:
        return FrontendRuleResult(module={"bad": True})  # type: ignore[arg-type]

    spec = FrontendSpec(
        frontend_id="demo.bad",
        dialect_id="htp.core",
        surface_type=DemoSurface,
        rule=FrontendRule(name="bad_build", build=bad_build),
    )

    with pytest.raises(TypeError, match="ProgramModule"):
        spec.build(DemoSurface("broken"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ir/test_frontend_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'htp.ir.frontend_rules'`

- [ ] **Step 3: Write minimal implementation**

Create `htp/ir/frontend_rules.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .module import ProgramModule


@dataclass(frozen=True)
class FrontendBuildContext:
    frontend_id: str
    dialect_id: str
    surface: Any
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FrontendRuleResult:
    module: ProgramModule
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FrontendRule:
    name: str
    build: Callable[[FrontendBuildContext], FrontendRuleResult]

    def apply(self, context: FrontendBuildContext) -> FrontendRuleResult:
        return self.build(context)
```

Modify `htp/ir/frontends.py`:

```python
from .frontend_rules import FrontendBuildContext, FrontendRule
from .module import ProgramModule


@dataclass(frozen=True)
class FrontendSpec:
    frontend_id: str
    dialect_id: str
    surface_type: type[Any]
    build_program_module: Callable[[Any], ProgramModule] | None = None
    rule: FrontendRule | None = None

    def build(self, surface: Any) -> ProgramModule:
        if self.rule is not None:
            result = self.rule.apply(
                FrontendBuildContext(
                    frontend_id=self.frontend_id,
                    dialect_id=self.dialect_id,
                    surface=surface,
                )
            )
            if not isinstance(result.module, ProgramModule):
                raise TypeError(f"{self.frontend_id} rule must return a ProgramModule")
            return result.module
        if self.build_program_module is None:
            raise TypeError(f"{self.frontend_id} has no builder or rule")
        module = self.build_program_module(surface)
        if not isinstance(module, ProgramModule):
            raise TypeError(f"{self.frontend_id} must build a ProgramModule")
        return module
```

Update `tests/ir/test_frontends.py` to call `spec.build(...)` instead of `spec.build_program_module(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ir/test_frontend_rules.py tests/ir/test_frontends.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/ir/frontend_rules.py htp/ir/frontends.py tests/ir/test_frontend_rules.py tests/ir/test_frontends.py
git commit -m "feat: add frontend rule substrate"
```

### Task 2: Route compiler ingress through the new frontend build contract

**Files:**
- Modify: `htp/compiler.py`
- Test: `tests/compiler/test_compile_program.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/compiler/test_compile_program.py`:

```python
from __future__ import annotations

from pathlib import Path

import htp
from htp.ir.frontend_rules import FrontendBuildContext, FrontendRule, FrontendRuleResult
from htp.ir.frontends import FrontendSpec, register_frontend
from htp.ir.module import ProgramModule


class DemoSurface:
    def __init__(self, entry: str) -> None:
        self.entry = entry


def test_compile_program_uses_registered_frontend_rule(tmp_path: Path) -> None:
    def build_demo(context: FrontendBuildContext) -> FrontendRuleResult:
        module = ProgramModule.from_program_dict(
            {
                "entry": context.surface.entry,
                "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": context.surface.entry}},
                "kernel_ir": {},
                "workload_ir": {},
                "target": {"backend": "cpu_ref"},
            },
            meta={"source_surface": "demo.rule"},
        )
        return FrontendRuleResult(module=module)

    register_frontend(
        FrontendSpec(
            frontend_id="demo.surface",
            dialect_id="htp.core",
            surface_type=DemoSurface,
            rule=FrontendRule(name="build_demo", build=build_demo),
        ),
        replace=True,
    )

    compiled = htp.compile_program(
        package_dir=tmp_path / "demo_surface_pkg",
        target="cpu_ref",
        program=DemoSurface("demo_entry"),
    )

    assert compiled.manifest["inputs"]["entry"] == "demo_entry"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/compiler/test_compile_program.py::test_compile_program_uses_registered_frontend_rule -v`
Expected: FAIL because `_normalize_program_input(...)` does not yet use `FrontendSpec.build(...)`

- [ ] **Step 3: Write minimal implementation**

Modify `htp/compiler.py`:

```python
from htp.ir.frontends import ensure_builtin_frontends, resolve_frontend


def compile_program(...):
    ensure_builtin_dialects()
    ensure_builtin_frontends()
    ...


def _normalize_program_input(...):
    ...
    frontend = resolve_frontend(program)
    if frontend is not None:
        module = frontend.build(program)
        return module.to_state_dict()
    ...
```

Also keep the fallback `to_program_module()` and `to_program()` logic exactly as-is after the registered-frontend path.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/compiler/test_compile_program.py::test_compile_program_uses_registered_frontend_rule -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/compiler.py tests/compiler/test_compile_program.py
git commit -m "feat: route compiler ingress through frontend specs"
```

### Task 3: Put `htp.kernel` on the node-first frontend-definition API

**Files:**
- Modify: `htp/kernel.py`
- Modify: `htp/ir/frontends.py`
- Modify: `tests/test_public_surfaces.py`
- Test: `tests/test_public_surfaces.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_public_surfaces.py`:

```python
from htp.ir.frontends import resolve_frontend
from htp.kernel import KernelSpec


def test_kernel_surface_is_built_through_registered_frontend_rule() -> None:
    spec = resolve_frontend(KernelSpec(name="affine", args=(), ops=()))

    assert spec is not None
    assert spec.frontend_id == "htp.kernel.KernelSpec"
    assert spec.rule is not None
    assert spec.build_program_module is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_surfaces.py::test_kernel_surface_is_built_through_registered_frontend_rule -v`
Expected: FAIL because builtin kernel frontend is still registered with `build_program_module=` instead of `rule=`

- [ ] **Step 3: Write minimal implementation**

Modify `htp/kernel.py` to expose a dedicated builder function instead of embedding all build logic inside `to_program_module()`:

```python
def build_kernel_program_module(spec: KernelSpec) -> ProgramModule:
    authored_program = spec.to_program()
    runtime_args = tuple(argument for argument in spec.args if argument.name is not None)
    kernel_ir = KernelIR(...)
    workload_ir = WorkloadIR(...)
    return ProgramModule(...)


def to_program_module(self) -> ProgramModule:
    return build_kernel_program_module(self)
```

Modify `htp/ir/frontends.py` builtin registration:

```python
from htp.kernel import KernelSpec, build_kernel_program_module
from .frontend_rules import FrontendRule, FrontendRuleResult

FrontendSpec(
    frontend_id="htp.kernel.KernelSpec",
    dialect_id="htp.kernel",
    surface_type=KernelSpec,
    rule=FrontendRule(
        name="kernel_spec_to_program_module",
        build=lambda context: FrontendRuleResult(
            module=build_kernel_program_module(context.surface)
        ),
    ),
)
```

Keep `KernelSpec.to_program_module()` as a delegating shim for now. Do not remove it in this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_public_surfaces.py::test_kernel_surface_is_built_through_registered_frontend_rule -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add htp/kernel.py htp/ir/frontends.py tests/test_public_surfaces.py
git commit -m "feat: migrate kernel ingress to frontend rule api"
```

### Task 4: Add one direct node-first frontend rule example and regression test

**Files:**
- Modify: `examples/ir_program_module_flow/demo.py`
- Modify: `examples/ir_program_module_flow/README.md`
- Modify: `tests/examples/test_examples.py`
- Test: `tests/examples/test_examples.py`

- [ ] **Step 1: Write the failing test**

Extend `tests/examples/test_examples.py`:

```python
def test_ir_program_module_example_reports_frontend_rule_proof() -> None:
    summary = run_ir_program_module_demo()

    assert summary["frontend_rule_demo"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/examples/test_examples.py::test_ir_program_module_example_reports_frontend_rule_proof -v`
Expected: FAIL because the example summary has no `frontend_rule_demo`

- [ ] **Step 3: Write minimal implementation**

Modify `examples/ir_program_module_flow/demo.py`:

```python
from htp.ir.frontends import resolve_frontend
from htp.kernel import KernelSpec


def frontend_rule_demo() -> bool:
    spec = resolve_frontend(KernelSpec(name="affine_demo", args=(), ops=()))
    return bool(spec is not None and spec.rule is not None)


def run_demo() -> dict[str, Any]:
    ...
    return {
        ...,
        "frontend_rule_demo": frontend_rule_demo(),
    }
```

Update `examples/ir_program_module_flow/README.md` to mention that the example now also proves registered frontend-rule ingress for a public surface.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/examples/test_examples.py::test_ir_program_module_example_reports_frontend_rule_proof -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add examples/ir_program_module_flow/demo.py examples/ir_program_module_flow/README.md tests/examples/test_examples.py
git commit -m "test: prove frontend rule ingress in ir flow example"
```

### Task 5: Sync the design docs to the implemented frontend-definition substrate

**Files:**
- Modify: `docs/in_progress/design/03_dialects_and_frontends.md`
- Modify: `docs/in_progress/design/05_implementation_and_migration.md`
- Modify: `docs/in_progress/design/README.md`
- Modify: `docs/in_progress/028-ast-all-the-way-contracts.md`
- Modify: `docs/design/programming_surfaces.md`
- Modify: `docs/design/compiler_model.md`

- [ ] **Step 1: Write the failing documentation assertions**

Add or update the explicit implemented-status bullets so these statements become true:

```markdown
- a rule-backed frontend-definition substrate now exists in `htp/ir/frontend_rules.py`
- builtin public surfaces are resolved through registered `FrontendSpec` objects in `htp/ir/frontends.py`
- `htp.kernel` is the first public surface migrated onto the rule-backed API
- remaining gap: routine/WSP/CSP still rely on shared builder helpers rather than the final node-first rule API
```

- [ ] **Step 2: Run doc grep to confirm the old claim is still stale**

Run: `rg -n "registry slice|design-only|frontend-definition mechanism|node-first frontend" docs/in_progress/design docs/design`
Expected: output still includes stale “slice only” wording that does not mention rule-backed implementation

- [ ] **Step 3: Write the minimal doc updates**

Add concrete code pointers like:

```markdown
- `htp/ir/frontend_rules.py`
- `htp/ir/frontends.py`
- `htp/kernel.py`
- `htp/compiler.py`
```

Make sure `docs/in_progress/028-ast-all-the-way-contracts.md` marks the new milestone complete and that `docs/design/*` describe only what is actually implemented.

- [ ] **Step 4: Run doc grep to verify the new statements are present**

Run: `rg -n "frontend_rules.py|rule-backed frontend|htp.kernel is the first public surface" docs/in_progress/design docs/design`
Expected: matches in both in-progress and design docs

- [ ] **Step 5: Commit**

```bash
git add docs/in_progress/design/03_dialects_and_frontends.md docs/in_progress/design/05_implementation_and_migration.md docs/in_progress/design/README.md docs/in_progress/028-ast-all-the-way-contracts.md docs/design/programming_surfaces.md docs/design/compiler_model.md
git commit -m "docs: sync frontend definition substrate status"
```

### Task 6: Run full verification and prepare the branch for the next slice

**Files:**
- Modify: none
- Test: repo-wide verification

- [ ] **Step 1: Run focused frontend checks**

Run:

```bash
pytest tests/ir/test_frontend_rules.py tests/ir/test_frontends.py tests/test_public_surfaces.py tests/compiler/test_compile_program.py -q
```

Expected: PASS

- [ ] **Step 2: Run example proof checks**

Run:

```bash
pytest tests/examples/test_examples.py::test_ir_program_module_example_defines_executes_and_transforms -q
python -m examples.ir_program_module_flow.demo
```

Expected:
- pytest PASS
- Python command prints a dict including `"frontend_rule_demo": True`

- [ ] **Step 3: Run full repository verification**

Run:

```bash
pytest -q
pre-commit run --all-files
pixi run verify
```

Expected:
- all tests PASS
- all hooks PASS
- Pixi verify PASS

- [ ] **Step 4: Review branch state**

Run:

```bash
git status --short --branch
git log --oneline -5
```

Expected:
- clean working tree
- four or more small commits for this frontend-definition slice

- [ ] **Step 5: Commit any final doc/test drift if needed**

```bash
git add -A
git commit -m "chore: finalize frontend definition slice"
```

Only do this if Step 3 or Step 4 required a small cleanup edit. Otherwise skip this commit.

---

## Self-Review

### Spec coverage

Covered by this plan:
- frontend-definition mechanism moves from design-only to code-backed substrate
- compiler ingress becomes registry-driven through explicit frontend specs
- one public surface (`htp.kernel`) becomes the proof migration target
- docs are synced to the new implemented state
- example/test evidence is added for the new frontend rule path

Not covered by this plan:
- migrating `htp.routine`, `htp.wsp`, and `htp.csp` onto the final rule-backed node-first API
- richer parser-combinator rule objects beyond the first `FrontendRule` / `FrontendBuildContext` layer
- intrinsic registry redesign
- backend depth and flagship-example realism

Those are separate follow-on tasks after this plan lands.

### Placeholder scan

Checked for `TODO`, `TBD`, “implement later”, “similar to”, and vague “write tests for the above” language. Removed them.

### Type consistency

Checked naming consistency across tasks:
- `FrontendBuildContext`
- `FrontendRule`
- `FrontendRuleResult`
- `FrontendSpec.build(...)`
- `build_kernel_program_module(...)`

No conflicting names remain in later tasks.
