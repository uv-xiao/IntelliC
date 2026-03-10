from __future__ import annotations

import json

import numpy as np

import htp
from tests.programs import portable_vector_add_program


def test_cpu_ref_backend_compiles_and_runs(tmp_path):
    package_dir = tmp_path / "cpu_ref_pkg"
    compiled = htp.compile_program(
        package_dir=package_dir, target="cpu_ref", program=portable_vector_add_program()
    )

    report = htp.bind(compiled.package_dir).validate()
    build = htp.bind(compiled.package_dir).build(mode="sim")
    lhs = np.arange(8, dtype=np.float32)
    rhs = np.arange(8, dtype=np.float32) * 2
    out = np.zeros(8, dtype=np.float32)
    run = htp.bind(compiled.package_dir).load(mode="sim").run("vector_add", args=(lhs, rhs, out, lhs.size))

    assert report.ok is True
    assert build.ok is True
    assert build.built_outputs == ["build/cpu_ref/runtime.json"]
    assert run.ok is True
    np.testing.assert_allclose(out, lhs + rhs)
    perf_payload = json.loads((compiled.package_dir / "metrics" / "perf.json").read_text())
    assert perf_payload["backend"] == "cpu_ref"
    assert perf_payload["entry"] == "vector_add"
