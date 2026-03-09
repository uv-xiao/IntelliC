from htp.runtime import ReplayDiagnosticError

STAGE_ID = "s02"


def run(*args, **kwargs):
    raise ReplayDiagnosticError(
        "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY",
        payload={
            "detail": "Replay for the emitted NV-GPU kernel is owned by the backend binding.",
            "node_id": "kernel::demo_kernel.kernel0",
            "entity_id": "demo_kernel.kernel0",
            "kind": "kernel",
            "artifact_ref": "ir/stages/s02/replay/stubs.json",
            "payload_ref": "ir/stages/s02/replay/stubs.json",
            "fix_hints_ref": "docs/design/impls/01_ir_model.md",
        },
        fix_hints=(
            "Replay through the owning extension or binding.",
            "Inspect the emitted backend artifacts referenced by the stub.",
        ),
    )
