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
                {"target": "tmp0", "op": "add", "lhs": "x", "rhs": "y"},
                {"target": "tmp1", "op": "add", "lhs": "x", "rhs": "y"},
                {"target": "out", "op": "mul", "lhs": "tmp1", "rhs": "z"},
            ],
            "result": "out",
        },
    )

    assert manifest == json.loads((package_dir / "manifest.json").read_text())
    assert manifest["stages"]["current"] == "s02"
    assert manifest["extensions"]["mlir_cse"] == {
        "module": "extensions/mlir_cse/module.mlir",
        "ledger": "extensions/mlir_cse/ledger.json",
        "eligibility": "extensions/mlir_cse/eligibility.json",
        "import_summary": "extensions/mlir_cse/import_summary.json",
    }

    assert (package_dir / "extensions" / "mlir_cse" / "module.mlir").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "ledger.json").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "eligibility.json").is_file()
    assert (package_dir / "extensions" / "mlir_cse" / "import_summary.json").is_file()

    import_summary = json.loads((package_dir / "extensions" / "mlir_cse" / "import_summary.json").read_text())
    assert import_summary["rewrites"] == [
        {
            "eliminated_target": "tmp1",
            "reused_target": "tmp0",
            "signature": "add(x, y)",
        }
    ]
    assert import_summary["result"] == "out"

    runtime = Runtime()
    register_replay_handler(runtime=runtime)

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay(
        "s02",
        kwargs={
            "x": 2,
            "y": 3,
            "z": 5,
            "runtime": runtime,
        },
    )

    assert result.ok is True
    assert result.result == {
        "result": 25,
        "rewrites": [
            {
                "eliminated_target": "tmp1",
                "reused_target": "tmp0",
                "signature": "add(x, y)",
            }
        ],
        "entry": "demo_kernel",
    }
