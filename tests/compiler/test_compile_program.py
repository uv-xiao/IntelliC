import json

import htp


def test_compile_program_emits_pto_package_and_keeps_stage_replay(tmp_path):
    package_dir = tmp_path / "pto_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="pto-a2a3sim",
        program={
            "entry": "demo_kernel",
            "ops": ["load_tile", "compute_tile", "store_tile"],
            "analysis": {},
            "package": {"emitted": False},
        },
    )

    assert compiled.target.backend == "pto"
    assert compiled.manifest["target"] == {
        "backend": "pto",
        "variant": "a2a3sim",
        "hardware_profile": "ascend:a2a3sim",
    }
    assert compiled.pipeline.current_stage == "s05"

    session = htp.bind(package_dir).load(mode="sim")
    replay = session.replay(compiled.pipeline.current_stage)
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["target"] == {"backend": "pto", "option": "a2a3sim"}


def test_compile_program_emits_nvgpu_package_and_keeps_stage_replay(tmp_path):
    package_dir = tmp_path / "nvgpu_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="nvgpu-ampere",
        program={
            "entry": "demo_kernel",
            "ops": ["load", "mma", "store"],
            "analysis": {},
            "package": {"emitted": False},
        },
    )

    assert compiled.target.backend == "nvgpu"
    assert compiled.manifest["target"] == {
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:ampere:sm80",
    }
    assert json.loads((package_dir / "manifest.json").read_text()) == compiled.manifest

    session = htp.bind(package_dir).load(mode="sim")
    replay = session.replay(compiled.pipeline.current_stage)
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["target"] == {"backend": "nvgpu", "option": "ampere"}


def test_compile_program_rejects_unknown_targets(tmp_path):
    package_dir = tmp_path / "bad_pkg"

    try:
        htp.compile_program(
            package_dir=package_dir,
            target="aie-xdna2",
        )
    except ValueError as exc:
        assert "Unsupported target backend" in str(exc)
    else:
        raise AssertionError("compile_program should reject unsupported backends")
