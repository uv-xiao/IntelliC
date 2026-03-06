# HTP V1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first end-to-end HTP implementation that proves the AST-first, replay-first, artifact-first design on both PTO and NV-GPU, with MLIR-based flows only as extension mechanisms.

**Architecture:** Implement the common compiler substrate first (`htp.ir`, `htp.pass`, `htp.artifacts`, `htp.runtime`, `htp.bindings`), then land one narrow backend path for PTO and one narrow backend path for NV-GPU. Keep the pass spine fixed (`ast_canonicalize`, `typecheck_layout_effects`, staged analysis, `apply_schedule`, backend lowering, package emission`) and require every stage to remain runnable in `sim`.

**Tech Stack:** Python 3.11+, `ast`, `dataclasses`, `typing`, `json`, `pathlib`, `pytest`, optional backend toolchains (`pto-runtime`, CUDA toolkit).

---

### Task 1: Create package skeleton and schema constants

**Files:**
- Create: `htp/__init__.py`
- Create: `htp/ir/__init__.py`
- Create: `htp/pass/__init__.py`
- Create: `htp/pipeline/__init__.py`
- Create: `htp/artifacts/__init__.py`
- Create: `htp/runtime/__init__.py`
- Create: `htp/bindings/__init__.py`
- Create: `htp/backends/__init__.py`
- Create: `htp/schemas.py`
- Test: `tests/test_imports.py`

**Step 1: Write the failing test**

```python
def test_public_packages_import():
    import htp
    import htp.ir
    import htp.pass
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_imports.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

- Create the package tree and expose empty package modules.
- Add schema ids used by the docs (`htp.manifest.v1`, `htp.pass_contract.v1`, `htp.replay.stubs.v1`, and the id/map schemas).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_imports.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp tests/test_imports.py
git commit -m "feat: scaffold htp package and schema ids"
```

### Task 2: Implement stage identity registries and mapping files

**Files:**
- Create: `htp/ir/ids.py`
- Create: `htp/ir/maps.py`
- Create: `htp/ir/state.py`
- Test: `tests/ir/test_ids.py`
- Test: `tests/ir/test_maps.py`

**Step 1: Write the failing tests**

```python
def test_entities_registry_is_deterministic():
    ...

def test_binding_map_records_split_and_introduced_bindings():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ir/test_ids.py tests/ir/test_maps.py -v`
Expected: FAIL with missing modules/functions

**Step 3: Write minimal implementation**

- Implement `node_id`, `entity_id`, `binding_id` assignment.
- Implement serializers for `ids/entities.json`, `ids/bindings.json`, `maps/entity_map.json`, `maps/binding_map.json`.
- Ensure stable ordering in emitted JSON.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ir/test_ids.py tests/ir/test_maps.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/ir tests/ir/test_ids.py tests/ir/test_maps.py
git commit -m "feat: add identity and rewrite map substrate"
```

### Task 3: Implement artifact writer and normalized stage manifest

**Files:**
- Create: `htp/artifacts/manifest.py`
- Create: `htp/artifacts/stages.py`
- Create: `htp/artifacts/validate.py`
- Test: `tests/artifacts/test_manifest.py`
- Test: `tests/artifacts/test_stage_layout.py`

**Step 1: Write the failing tests**

```python
def test_manifest_contains_normalized_stage_records():
    ...

def test_stubbed_stage_requires_replay_stubs_path():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/artifacts/test_manifest.py tests/artifacts/test_stage_layout.py -v`
Expected: FAIL with missing writer/validator

**Step 3: Write minimal implementation**

- Implement `manifest.json` emission with normalized per-stage records.
- Emit empty `analysis/index.json` when a stage has no analyses.
- Enforce `replay/stubs.json` presence for stubbed stages.

**Step 4: Run tests to verify it passes**

Run: `pytest tests/artifacts/test_manifest.py tests/artifacts/test_stage_layout.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/artifacts tests/artifacts
git commit -m "feat: add manifest and stage artifact writer"
```

### Task 4: Implement pass contracts, pass manager, and trace emission

**Files:**
- Create: `htp/pass/contracts.py`
- Create: `htp/pass/manager.py`
- Create: `htp/pass/trace.py`
- Test: `tests/pass/test_contracts.py`
- Test: `tests/pass/test_manager.py`

**Step 1: Write the failing tests**

```python
def test_analysis_pass_declares_outputs_and_preserves_ast():
    ...

def test_pass_trace_emits_normalized_event():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/pass/test_contracts.py tests/pass/test_manager.py -v`
Expected: FAIL with missing contract/manager

**Step 3: Write minimal implementation**

- Implement `PassContract`.
- Implement immutable stage creation per pass.
- Emit `ir/pass_trace.jsonl` with the required v1 event fields.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/pass/test_contracts.py tests/pass/test_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/pass tests/pass
git commit -m "feat: add pass contracts and trace emission"
```

### Task 5: Implement replay runtime and stage module contract

**Files:**
- Create: `htp/runtime/core.py`
- Create: `htp/runtime/intrinsics.py`
- Create: `htp/runtime/extensions.py`
- Create: `htp/runtime/errors.py`
- Test: `tests/runtime/test_replay_runtime.py`
- Test: `tests/runtime/test_stub_diagnostics.py`

**Step 1: Write the failing tests**

```python
def test_stage_run_defaults_to_default_runtime():
    ...

def test_raise_stub_produces_structured_diagnostic():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/runtime/test_replay_runtime.py tests/runtime/test_stub_diagnostics.py -v`
Expected: FAIL with missing runtime surface

**Step 3: Write minimal implementation**

- Implement `default_runtime`, `call_kernel`, `intrinsics.invoke`, `extensions.invoke`, and `raise_stub`.
- Implement the base replay diagnostic exception carrying code, payload, and fix hints.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_replay_runtime.py tests/runtime/test_stub_diagnostics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/runtime tests/runtime
git commit -m "feat: add replay runtime surface"
```

### Task 6: Implement binding API skeleton and replay path

**Files:**
- Create: `htp/bindings/api.py`
- Create: `htp/bindings/base.py`
- Create: `htp/bindings/validate.py`
- Test: `tests/bindings/test_api.py`
- Test: `tests/bindings/test_replay.py`

**Step 1: Write the failing tests**

```python
def test_bind_returns_binding_for_manifest_backend():
    ...

def test_replay_result_contains_log_and_stage_id():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/bindings/test_api.py tests/bindings/test_replay.py -v`
Expected: FAIL with missing bind/load/replay API

**Step 3: Write minimal implementation**

- Implement `htp.bind(...)`.
- Implement `validate`, `build`, `load`, `run`, and `replay` result records.
- Add log path plumbing for replay.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/bindings/test_api.py tests/bindings/test_replay.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/bindings tests/bindings
git commit -m "feat: add binding api and replay path"
```

### Task 7: Implement the mandatory pass spine on a narrow example language slice

**Files:**
- Create: `htp/pipeline/defaults.py`
- Create: `htp/passes/ast_canonicalize.py`
- Create: `htp/passes/typecheck_layout_effects.py`
- Create: `htp/passes/analyze_schedule.py`
- Create: `htp/passes/apply_schedule.py`
- Create: `htp/passes/emit_package.py`
- Test: `tests/pipeline/test_default_pipeline.py`

**Step 1: Write the failing test**

```python
def test_default_pipeline_runs_all_mandatory_passes():
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_default_pipeline.py -v`
Expected: FAIL with missing pipeline/passes

**Step 3: Write minimal implementation**

- Register the pass spine in order.
- Make the staged analysis pass produce a concrete artifact under `analysis/`.
- Ensure every pass emits a stage.

**Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_default_pipeline.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/pipeline htp/passes tests/pipeline
git commit -m "feat: add mandatory v1 pass spine"
```

### Task 8: Land PTO backend and binding

**Files:**
- Create: `htp/backends/pto/__init__.py`
- Create: `htp/backends/pto/arch.py`
- Create: `htp/backends/pto/lower.py`
- Create: `htp/backends/pto/emit.py`
- Create: `htp/bindings/pto.py`
- Test: `tests/backends/pto/test_emit.py`
- Test: `tests/backends/pto/test_binding_contract.py`

**Step 1: Write the failing tests**

```python
def test_pto_emit_produces_kernel_config_and_index():
    ...

def test_pto_binding_validates_required_files():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/backends/pto/test_emit.py tests/backends/pto/test_binding_contract.py -v`
Expected: FAIL with missing PTO backend

**Step 3: Write minimal implementation**

- Emit `codegen/pto/kernel_config.py` and `codegen/pto/pto_codegen.json`.
- Implement `a2a3sim` first; leave device-specific behavior behind the same binding API.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/backends/pto/test_emit.py tests/backends/pto/test_binding_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/backends/pto htp/bindings/pto.py tests/backends/pto
git commit -m "feat: add pto backend contract and binding"
```

### Task 9: Land NV-GPU backend and binding with `.cu` as the authoritative artifact

**Files:**
- Create: `htp/backends/nvgpu/__init__.py`
- Create: `htp/backends/nvgpu/arch.py`
- Create: `htp/backends/nvgpu/lower.py`
- Create: `htp/backends/nvgpu/emit.py`
- Create: `htp/bindings/nvgpu.py`
- Test: `tests/backends/nvgpu/test_emit.py`
- Test: `tests/backends/nvgpu/test_profiles.py`

**Step 1: Write the failing tests**

```python
def test_nvgpu_emit_prefers_cu_source_artifacts():
    ...

def test_ampere_and_blackwell_are_profiles_of_one_backend():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/backends/nvgpu/test_emit.py tests/backends/nvgpu/test_profiles.py -v`
Expected: FAIL with missing NV-GPU backend

**Step 3: Write minimal implementation**

- Emit `.cu` into `codegen/nvgpu/kernels/`.
- Record profile-specific capabilities via `hardware_profile`.
- Treat `.ptx` / `.cubin` only as derived build outputs under `build/`.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/backends/nvgpu/test_emit.py tests/backends/nvgpu/test_profiles.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp/backends/nvgpu htp/bindings/nvgpu.py tests/backends/nvgpu
git commit -m "feat: add nvgpu backend with cu artifact contract"
```

### Task 10: Add golden artifact, replay, and diagnostics gates

**Files:**
- Create: `tests/golden/test_artifacts.py`
- Create: `tests/golden/test_replay.py`
- Create: `tests/golden/test_diagnostics.py`
- Modify: `tests/conftest.py`

**Step 1: Write the failing tests**

```python
def test_golden_package_has_required_stage_files():
    ...

def test_diagnostic_contains_fix_hints_ref():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/golden -v`
Expected: FAIL with missing golden fixtures or required fields

**Step 3: Write minimal implementation**

- Add golden fixtures for one PTO example and one NV-GPU example.
- Verify replay in `sim`.
- Verify diagnostics include payload and fix hints.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/golden -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/golden tests/conftest.py
git commit -m "test: add golden artifact and replay gates"
```

### Task 11: Add one MLIR extension package with a simple CSE island

**Files:**
- Create: `htp_ext/mlir_cse/__init__.py`
- Create: `htp_ext/mlir_cse/island.py`
- Create: `htp_ext/mlir_cse/export.py`
- Create: `htp_ext/mlir_cse/import_.py`
- Test: `tests/extensions/test_mlir_cse.py`

**Step 1: Write the failing test**

```python
def test_mlir_cse_extension_round_trips_and_replays():
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/extensions/test_mlir_cse.py -v`
Expected: FAIL with missing extension package

**Step 3: Write minimal implementation**

- Keep MLIR out of the HTP core package.
- Implement only the narrow exporter/importer subset documented for the CSE extension.
- Record `ledger.json`, `eligibility.json`, and `import_summary.json`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/extensions/test_mlir_cse.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add htp_ext tests/extensions
git commit -m "feat: add mlir cse extension island"
```
