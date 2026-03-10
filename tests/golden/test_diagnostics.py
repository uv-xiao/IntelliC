import htp
from tests.conftest import copy_golden_fixture


def test_diagnostic_contains_fix_hints_ref(tmp_path):
    package_dir = copy_golden_fixture("nvgpu_demo", tmp_path)
    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("s02")

    assert result.ok is False
    assert result.stage_id == "s02"
    assert result.diagnostics == [
        {
            "code": "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY",
            "detail": "Replay for the emitted NV-GPU kernel is owned by the backend binding.",
            "node_id": "kernel::demo_kernel.kernel0",
            "entity_id": "demo_kernel.kernel0",
            "kind": "kernel",
            "artifact_ref": "ir/stages/s02/replay/stubs.json",
            "payload_ref": "ir/stages/s02/replay/stubs.json",
            "fix_hints_ref": "docs/design/compiler_model.md",
            "fix_hints": [
                "Replay through the owning extension or binding.",
                "Inspect the emitted backend artifacts referenced by the stub.",
            ],
        }
    ]
