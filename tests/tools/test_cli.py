from __future__ import annotations

import json

from htp.__main__ import main
from htp.compiler import compile_program


def _vector_add_program() -> dict[str, object]:
    return {
        "entry": "vector_add",
        "kernel": {
            "name": "vector_add",
            "args": [
                {"name": "lhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                {"name": "rhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                {"name": "out", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "output"},
                {"name": "size", "kind": "scalar", "dtype": "i32", "role": "shape"},
            ],
            "ops": [
                {
                    "op": "elementwise_binary",
                    "operator": "add",
                    "lhs": "lhs",
                    "rhs": "rhs",
                    "out": "out",
                    "shape": ["size"],
                    "dtype": "f32",
                }
            ],
        },
        "workload": {
            "entry": "vector_add",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "vector_add",
                    "args": ["lhs", "rhs", "out", "size"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "analysis": {},
        "package": {"emitted": False},
    }


def test_cli_explain_emits_json(capsys):
    exit_code = main(["explain", "HTP.BINDINGS.MISSING_CONTRACT_FILE"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "HTP.BINDINGS.MISSING_CONTRACT_FILE"
    assert payload["known"] is True
    assert payload["fix_hint_policy"] == "rebuild_or_validate_artifacts"


def test_cli_verify_emits_json_report(tmp_path, capsys):
    package_dir = tmp_path / "pto_pkg"
    compile_program(package_dir=package_dir, target="pto-a2a3sim", program=_vector_add_program())

    exit_code = main(["verify", str(package_dir), "--goal", "cli-check"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["gates"] == {"validate": True, "replay": True}


def test_cli_bisect_emits_json(tmp_path, capsys):
    left_dir = tmp_path / "left_pkg"
    right_dir = tmp_path / "right_pkg"
    compile_program(package_dir=left_dir, target="nvgpu-ampere", program=_vector_add_program())
    compile_program(package_dir=right_dir, target="nvgpu-ampere", program=_vector_add_program())
    manifest = json.loads((right_dir / "manifest.json").read_text())
    current_stage = manifest["stages"]["current"]
    kernel_ir_path = (
        right_dir
        / next(stage for stage in manifest["stages"]["graph"] if stage["id"] == current_stage)["semantic"][
            "kernel_ir"
        ]
    )
    kernel_ir = json.loads(kernel_ir_path.read_text())
    kernel_ir["ops"][0]["attrs"]["operator"] = "mul"
    kernel_ir_path.write_text(json.dumps(kernel_ir, indent=2) + "\n")

    exit_code = main(["bisect", str(left_dir), str(right_dir)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["equal"] is False
    assert payload["first_divergent_stage"] == {"left": "s06", "right": "s06"}


def test_cli_minimize_emits_json(tmp_path, capsys):
    package_dir = tmp_path / "pto_pkg"
    compile_program(package_dir=package_dir, target="pto-a2a3sim", program=_vector_add_program())
    output_dir = tmp_path / "minimized"

    exit_code = main(["minimize", str(package_dir), str(output_dir), "--stage", "s03"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stage_id"] == "s03"
    assert payload["output_dir"] == str(output_dir)
