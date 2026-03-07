import json

import htp
import htp.bindings


def test_bind_returns_binding_for_manifest_backend(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "htp.manifest.v1",
                "target": {
                    "backend": "pto",
                    "variant": "a2a3sim",
                },
                "stages": {
                    "current": "s00",
                    "graph": [],
                },
            },
            indent=2,
        )
        + "\n"
    )

    binding = htp.bind(package_dir)

    assert binding.backend == "pto"
    assert binding.variant == "a2a3sim"

    report = binding.validate()
    assert report.ok is True
    assert report.backend == "pto"
    assert report.variant == "a2a3sim"
    assert report.missing_files == []
