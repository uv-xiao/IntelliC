import json

from htp.bindings.api import bind
from tests.conftest import copy_golden_fixture


def _artifact_paths(manifest: dict) -> tuple[list[str], list[str]]:
    stages = manifest["stages"]["graph"]
    file_paths: list[str] = []
    dir_paths: list[str] = []
    for stage in stages:
        dir_paths.append(stage["dir"])
        file_paths.extend(
            [
                stage["analysis_index"],
                stage["summary"],
                stage["runnable_py"]["program_py"],
                stage["ids"]["entities"],
                stage["ids"]["bindings"],
            ]
        )
        if stage["runnable_py"]["stubs"] is not None:
            file_paths.append(stage["runnable_py"]["stubs"])
    return dir_paths, file_paths


def test_golden_package_has_required_stage_files(tmp_path):
    for fixture_name in ("pto_demo", "nvgpu_demo"):
        package_dir = copy_golden_fixture(fixture_name, tmp_path)
        manifest = json.loads((package_dir / "manifest.json").read_text())
        assert manifest["schema"] == "htp.manifest.v1"
        dir_paths, file_paths = _artifact_paths(manifest)
        for relpath in dir_paths:
            assert (package_dir / relpath).is_dir(), relpath
        for relpath in file_paths:
            assert (package_dir / relpath).is_file(), relpath

        report = bind(package_dir).validate()
        assert report.ok is True
        assert report.diagnostics == []


def test_golden_backend_artifacts_match_contract(tmp_path):
    pto_dir = copy_golden_fixture("pto_demo", tmp_path)
    nvgpu_dir = copy_golden_fixture("nvgpu_demo", tmp_path)

    assert (pto_dir / "codegen" / "pto" / "kernel_config.py").is_file()
    assert (pto_dir / "codegen" / "pto" / "pto_codegen.json").is_file()
    assert (pto_dir / "build" / "toolchain.json").is_file()

    kernel_dir = nvgpu_dir / "codegen" / "nvgpu" / "kernels"
    assert sorted(path.suffix for path in kernel_dir.iterdir()) == [".cu"]
    assert (nvgpu_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json").is_file()
    assert (nvgpu_dir / "build" / "toolchain.json").is_file()
