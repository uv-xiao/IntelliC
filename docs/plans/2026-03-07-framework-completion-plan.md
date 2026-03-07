# HTP Framework Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the next HTP milestone by stabilizing the compile/replay UX first, then deepening backend execution realism, and finally strengthening the semantics of the default pass spine.

**Architecture:** Keep Python-space canonical. Treat stage replay and emitted artifacts as contractual. Land user-facing compile/package/replay behavior before backend build/load/run realism, then deepen pass semantics without introducing a new semantic owner.

**Tech Stack:** Python 3.11+, `ast`, `dataclasses`, `typing`, `json`, `pathlib`, `pytest`, `pre-commit`.

---

### Task 1: Finish the public compile entrypoint

**Files:**
- Create: `htp/compiler.py`
- Modify: `htp/__init__.py`
- Modify: `README.md`
- Test: `tests/compiler/test_compile_program.py`
- Test: `tests/test_imports.py`

**Step 1: Write the failing tests**

```python
def test_compile_program_emits_valid_pto_package(tmp_path):
    ...

def test_compile_program_rejects_unknown_target():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_imports.py tests/compiler/test_compile_program.py -v`
Expected: FAIL with missing compile API or unsupported target handling

**Step 3: Write minimal implementation**

- Add `parse_target(...)` and `compile_program(...)`.
- Normalize target strings into backend plus profile/option.
- Route PTO and NVGPU package emission through the existing backend emitters.
- Validate the emitted package immediately after emission.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_imports.py tests/compiler/test_compile_program.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/compiler.py htp/__init__.py README.md tests/compiler/test_compile_program.py tests/test_imports.py
git commit -m "feat: add public compile entrypoint"
```

### Task 2: Make stage modules replayable by default

**Files:**
- Create: `htp/passes/replay_program.py`
- Modify: `htp/passes/ast_canonicalize.py`
- Modify: `htp/passes/typecheck_layout_effects.py`
- Modify: `htp/passes/analyze_schedule.py`
- Modify: `htp/passes/apply_schedule.py`
- Modify: `htp/passes/emit_package.py`
- Modify: `htp/pipeline/defaults.py`
- Test: `tests/pipeline/test_default_pipeline.py`

**Step 1: Write the failing test**

```python
def test_default_pipeline_final_stage_replays_program_snapshot(tmp_path):
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_default_pipeline.py -v`
Expected: FAIL because final stage `program.py` is not runnable or does not expose the staged snapshot

**Step 3: Write minimal implementation**

- Add a helper to render replayable stage modules from staged program state.
- Replace placeholder `program.py` bodies in the default pass spine with runnable stage modules.
- Ensure the default example program contains enough target metadata for replay and downstream emission.

**Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_default_pipeline.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/passes/replay_program.py htp/passes/ast_canonicalize.py htp/passes/typecheck_layout_effects.py htp/passes/analyze_schedule.py htp/passes/apply_schedule.py htp/passes/emit_package.py htp/pipeline/defaults.py tests/pipeline/test_default_pipeline.py
git commit -m "feat: emit replayable stage programs"
```

### Task 3: Support replay-only stage packages through the binding API

**Files:**
- Modify: `htp/bindings/api.py`
- Modify: `htp/bindings/base.py`
- Test: `tests/bindings/test_api.py`
- Test: `tests/pipeline/test_default_pipeline.py`

**Step 1: Write the failing tests**

```python
def test_bind_accepts_stage_only_manifest_for_replay(tmp_path):
    ...

def test_stage_package_replay_does_not_require_backend_marker(tmp_path):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/bindings/test_api.py tests/pipeline/test_default_pipeline.py -v`
Expected: FAIL with manifest backend selection error

**Step 3: Write minimal implementation**

- Add a generic manifest-backed replay binding path for stage-only packages.
- Keep explicit backend selection when real backend markers are present.
- Preserve structured validation failures for malformed manifests.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/bindings/test_api.py tests/pipeline/test_default_pipeline.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/bindings/api.py htp/bindings/base.py tests/bindings/test_api.py tests/pipeline/test_default_pipeline.py
git commit -m "fix: support replay-only stage packages"
```

### Task 4: Normalize PTO binding lifecycle results

**Files:**
- Modify: `htp/bindings/pto.py`
- Modify: `htp/bindings/base.py`
- Test: `tests/bindings/test_pto.py`
- Test: `tests/golden/test_diagnostics.py`

**Step 1: Write the failing tests**

```python
def test_pto_binding_returns_structured_build_result(tmp_path):
    ...

def test_pto_binding_reports_missing_runtime_as_diagnostic(tmp_path):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/bindings/test_pto.py tests/golden/test_diagnostics.py -v`
Expected: FAIL because PTO lifecycle actions do not yet expose normalized results or diagnostics

**Step 3: Write minimal implementation**

- Normalize PTO `validate/build/load/run/replay` outputs.
- Convert toolchain/runtime absence into structured diagnostics.
- Keep emitted artifact ownership in the backend package, not in core runtime.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/bindings/test_pto.py tests/golden/test_diagnostics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/bindings/pto.py htp/bindings/base.py tests/bindings/test_pto.py tests/golden/test_diagnostics.py
git commit -m "feat: normalize pto binding lifecycle results"
```

### Task 5: Normalize NVGPU binding lifecycle results

**Files:**
- Modify: `htp/bindings/nvgpu.py`
- Modify: `htp/backends/nvgpu/emit.py`
- Modify: `htp/bindings/base.py`
- Test: `tests/backends/nvgpu/test_nvgpu_emit.py`
- Test: `tests/bindings/test_nvgpu.py`

**Step 1: Write the failing tests**

```python
def test_nvgpu_binding_returns_structured_validate_and_build_results(tmp_path):
    ...

def test_nvgpu_validation_checks_manifest_codegen_parity(tmp_path):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/backends/nvgpu/test_nvgpu_emit.py tests/bindings/test_nvgpu.py -v`
Expected: FAIL because NVGPU lifecycle actions or parity validation are incomplete

**Step 3: Write minimal implementation**

- Normalize NVGPU `validate/build/load/run/replay` outputs.
- Keep `.cu` authoritative and treat build products as derived outputs.
- Validate parity between manifest metadata and `nvgpu_codegen.json`.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/backends/nvgpu/test_nvgpu_emit.py tests/bindings/test_nvgpu.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/bindings/nvgpu.py htp/backends/nvgpu/emit.py htp/bindings/base.py tests/backends/nvgpu/test_nvgpu_emit.py tests/bindings/test_nvgpu.py
git commit -m "feat: normalize nvgpu binding lifecycle results"
```

### Task 6: Deepen the semantic meaning of the default pass spine

**Files:**
- Modify: `htp/passes/ast_canonicalize.py`
- Modify: `htp/passes/typecheck_layout_effects.py`
- Modify: `htp/passes/analyze_schedule.py`
- Modify: `htp/passes/apply_schedule.py`
- Modify: `htp/passes/emit_package.py`
- Test: `tests/passes/test_manager.py`
- Test: `tests/pipeline/test_default_pipeline.py`
- Test: `tests/golden/test_artifacts.py`

**Step 1: Write the failing tests**

```python
def test_typecheck_emits_nontrivial_layout_and_effect_analysis(tmp_path):
    ...

def test_apply_schedule_changes_program_state_from_analysis(tmp_path):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/passes/test_manager.py tests/pipeline/test_default_pipeline.py tests/golden/test_artifacts.py -v`
Expected: FAIL because analysis payloads and transforms are still placeholder-level

**Step 3: Write minimal implementation**

- Strengthen canonicalization output.
- Emit real typed/layout/effect analysis payloads.
- Emit a meaningful schedule analysis.
- Rewrite staged program state based on the schedule analysis while keeping replay runnable.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/passes/test_manager.py tests/pipeline/test_default_pipeline.py tests/golden/test_artifacts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/passes/ast_canonicalize.py htp/passes/typecheck_layout_effects.py htp/passes/analyze_schedule.py htp/passes/apply_schedule.py htp/passes/emit_package.py tests/passes/test_manager.py tests/pipeline/test_default_pipeline.py tests/golden/test_artifacts.py
git commit -m "feat: deepen default pipeline semantics"
```

### Task 7: Run full verification and align docs

**Files:**
- Modify: `README.md`
- Modify: relevant `docs/design/impls/*.md` if emitted contracts changed

**Step 1: Run the full verification stack**

Run: `pytest`
Expected: PASS

**Step 2: Run repository hooks**

Run: `pre-commit run --all-files`
Expected: PASS

**Step 3: Update docs if any contract paths or behaviors changed**

- Align README and design docs with the actual compile API, replay behavior, and backend lifecycle results.

**Step 4: Commit**

```bash
git add README.md docs/design/impls/*.md
git commit -m "docs: align framework docs with implemented contracts"
```
