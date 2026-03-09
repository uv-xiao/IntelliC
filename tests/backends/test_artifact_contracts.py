from __future__ import annotations

from htp.backends.nvgpu.declarations import declaration_for as nvgpu_declaration_for
from htp.backends.nvgpu.emit import emit_package as emit_nvgpu_package
from htp.backends.pto.declarations import declaration_for as pto_declaration_for
from htp.backends.pto.emit import emit_package as emit_pto_package
from htp_ext.aie.declarations import declaration_for as aie_declaration_for
from htp_ext.aie.emit import emit_package as emit_aie_package


def test_backend_emitters_use_declared_artifact_contracts(tmp_path):
    pto_dir = tmp_path / "pto"
    nvgpu_dir = tmp_path / "nvgpu"
    aie_dir = tmp_path / "aie"

    pto_manifest = emit_pto_package(
        pto_dir, program={"entry": "vadd", "ops": ["compute_tile"]}, variant="a2a3sim"
    )
    nvgpu_manifest = emit_nvgpu_package(
        nvgpu_dir,
        program={"entry": "gemm", "ops": ["load", "mma", "store"], "profile": "ampere"},
        profile="ampere",
    )
    aie_manifest = emit_aie_package(
        aie_dir,
        program={
            "entry": "stream_add",
            "kernel": {"name": "stream_add", "args": [], "ops": []},
            "workload": {"entry": "stream_add", "tasks": [], "channels": [], "dependencies": []},
        },
        profile="xdna2-npu1",
    )

    assert pto_manifest["outputs"] == pto_declaration_for("a2a3sim").artifact_contract.as_manifest_outputs()
    assert (
        nvgpu_manifest["outputs"] == nvgpu_declaration_for("ampere").artifact_contract.as_manifest_outputs()
    )
    assert (
        aie_manifest["outputs"] == aie_declaration_for("xdna2-npu1").artifact_contract.as_manifest_outputs()
    )
