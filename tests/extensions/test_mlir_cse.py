import json

import htp
from htp.runtime import Runtime
from htp_ext.mlir_cse import emit_package, register_replay_handler


def test_mlir_cse_extension_round_trips_and_replays(tmp_path):
    package_dir = tmp_path / "mlir_cse_pkg"
    package_dir.mkdir()

    manifest = emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "exprs": [
                {"target": "sum0", "op": "add", "lhs": "lhs", "rhs": "rhs"},
                {"target": "sum1", "op": "add", "lhs": "lhs", "rhs": "rhs"},
                {"target": "out", "op": "mul", "lhs": "sum1", "rhs": "scale"},
            ],
            "result": "out",
        },
    )

    assert manifest == json.loads((package_dir / "manifest.json").read_text())
    assert manifest["stages"]["current"] == "s02"
    assert manifest["extensions"]["mlir_cse"] == {
        "input": "extensions/mlir_cse/input.mlir",
        "output": "extensions/mlir_cse/output.mlir",
        "pipeline": "extensions/mlir_cse/pipeline.txt",
        "ledger": "extensions/mlir_cse/ledger.json",
        "eligibility": "extensions/mlir_cse/eligibility.json",
        "import_summary": "extensions/mlir_cse/import_summary.json",
    }
    assert manifest["stages"]["graph"][0]["islands"] == [
        {"island_id": "mlir_cse", "dir": "ir/stages/s01/islands/mlir_cse"}
    ]
    assert manifest["stages"]["graph"][1]["islands"] == [
        {"island_id": "mlir_cse", "dir": "ir/stages/s02/islands/mlir_cse"}
    ]

    assert (package_dir / "extensions" / "mlir_cse" / "input.mlir").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "output.mlir").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "pipeline.txt").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "ledger.json").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "eligibility.json").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "import_summary.json").is_file()
    assert (package_dir / "ir" / "stages" / "s01" / "islands" / "mlir_cse" / "input.mlir").is_file()
    assert (package_dir / "ir" / "stages" / "s01" / "islands" / "mlir_cse" / "pipeline.txt").is_file()
    assert (package_dir / "ir" / "stages" / "s01" / "islands" / "mlir_cse" / "ledger.json").is_file()
    assert (package_dir / "ir" / "stages" / "s02" / "islands" / "mlir_cse" / "output.mlir").is_file()
    assert (package_dir / "ir" / "stages" / "s02" / "islands" / "mlir_cse" / "import_summary.json").is_file()

    import_summary = json.loads((package_dir / "extensions" / "mlir_cse" / "import_summary.json").read_text())
    assert import_summary["rewrites"] == [
        {
            "eliminated_target": "sum1",
            "reused_target": "sum0",
            "signature": "add(lhs, rhs)",
        }
    ]
    assert import_summary["result"] == "out"
    input_text = (package_dir / "extensions" / "mlir_cse" / "input.mlir").read_text()
    output_text = (package_dir / "extensions" / "mlir_cse" / "output.mlir").read_text()
    assert "func.func @demo_kernel(%lhs: i32, %rhs: i32, %scale: i32) -> i32" in input_text
    assert "return %v2 : i32" in input_text
    assert output_text.count("arith.addi") == 1
    assert "return %v2 : i32" in output_text

    runtime = Runtime()
    register_replay_handler(runtime=runtime)

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay(
        "s02",
        kwargs={
            "lhs": 2,
            "rhs": 3,
            "scale": 5,
            "runtime": runtime,
        },
    )

    assert result.ok is True
    assert result.result == {
        "result": 25,
        "rewrites": [
            {
                "eliminated_target": "sum1",
                "reused_target": "sum0",
                "signature": "add(lhs, rhs)",
            }
        ],
        "entry": "demo_kernel",
    }
    kernel_ir = json.loads((package_dir / "ir" / "stages" / "s02" / "kernel_ir.json").read_text())
    assert kernel_ir["ops"] == [
        {
            "op_id": "op0",
            "entity_id": "demo_kernel:E3",
            "op": "elementwise_binary",
            "intrinsic": "portable.elementwise_binary",
            "inputs": ["lhs", "rhs"],
            "outputs": ["sum0"],
            "attrs": {"dtype": "i32", "operator": "add", "shape": []},
            "effects": {"reads": ["lhs", "rhs"], "writes": ["sum0"]},
        },
        {
            "op_id": "op1",
            "entity_id": "demo_kernel:E4",
            "op": "elementwise_binary",
            "intrinsic": "portable.elementwise_binary",
            "inputs": ["sum0", "scale"],
            "outputs": ["out"],
            "attrs": {"dtype": "i32", "operator": "mul", "shape": []},
            "effects": {"reads": ["sum0", "scale"], "writes": ["out"]},
        },
    ]


def test_mlir_cse_extension_rejects_missing_result_symbol(tmp_path):
    package_dir = tmp_path / "mlir_cse_pkg"
    package_dir.mkdir()

    try:
        emit_package(
            package_dir,
            program={
                "entry": "bad_kernel",
                "exprs": [
                    {"target": "sum0", "op": "add", "lhs": "lhs", "rhs": "rhs"},
                ],
            },
        )
    except ValueError as exc:
        assert "non-empty string result symbol" in str(exc)
    else:
        raise AssertionError("emit_package should reject missing result symbols")


def test_mlir_cse_extension_accepts_canonical_kernel_subset(tmp_path):
    package_dir = tmp_path / "mlir_cse_kernel_pkg"
    package_dir.mkdir()

    manifest = emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "kernel": {
                "name": "demo_kernel",
                "args": [
                    {"name": "lhs", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                    {"name": "rhs", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                    {"name": "scale", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                ],
                "ops": [
                    {
                        "op": "elementwise_binary",
                        "operator": "add",
                        "lhs": "lhs",
                        "rhs": "rhs",
                        "out": "sum0",
                        "shape": [],
                        "dtype": "i32",
                    },
                    {
                        "op": "elementwise_binary",
                        "operator": "add",
                        "lhs": "lhs",
                        "rhs": "rhs",
                        "out": "sum1",
                        "shape": [],
                        "dtype": "i32",
                    },
                    {
                        "op": "elementwise_binary",
                        "operator": "mul",
                        "lhs": "sum1",
                        "rhs": "scale",
                        "out": "out",
                        "shape": [],
                        "dtype": "i32",
                    },
                ],
            },
            "workload": {
                "entry": "demo_kernel",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "demo_kernel",
                        "args": ["lhs", "rhs", "scale"],
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
            "result": "out",
        },
    )

    assert manifest["stages"]["current"] == "s02"
    import_summary = json.loads((package_dir / "extensions" / "mlir_cse" / "import_summary.json").read_text())
    assert import_summary["rewrites"] == [
        {
            "eliminated_target": "sum1",
            "reused_target": "sum0",
            "signature": "add(lhs, rhs)",
        }
    ]
