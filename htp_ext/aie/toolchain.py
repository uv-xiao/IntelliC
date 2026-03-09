from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from htp.bindings.validate import load_manifest

AIE_BUILD_PRODUCT_SCHEMA_ID = "htp.aie.build_product.v1"
AIE_HOST_RUNTIME_SCHEMA_ID = "htp.aie.host_runtime.v1"


def build_package(
    package_dir: Path | str,
    manifest: dict[str, Any] | None = None,
) -> list[str]:
    package_path = Path(package_dir)
    package_manifest = load_manifest(package_path) if manifest is None else manifest
    outputs = package_manifest.get("outputs", {})
    mlir_path = package_path / "codegen" / "aie" / "aie.mlir"
    mapping_path = package_path / "codegen" / "aie" / "mapping.json"
    fifos_path = package_path / "codegen" / "aie" / "fifos.json"
    codegen_index_path = package_path / "codegen" / "aie" / "aie_codegen.json"
    build_dir = package_path / "build" / "aie"
    build_dir.mkdir(parents=True, exist_ok=True)
    codegen_index = json.loads(codegen_index_path.read_text())
    entry = str(codegen_index.get("entry", "aie"))

    build_product = {
        "schema": AIE_BUILD_PRODUCT_SCHEMA_ID,
        "entry": entry,
        "target": dict(package_manifest.get("target", {})),
        "inputs": {
            "mlir": "codegen/aie/aie.mlir",
            "mapping": "codegen/aie/mapping.json",
            "fifos": "codegen/aie/fifos.json",
        },
        "digests": {
            "mlir_sha256": _sha256_text(mlir_path),
            "mapping_sha256": _sha256_text(mapping_path),
            "fifos_sha256": _sha256_text(fifos_path),
        },
        "declared_outputs": dict(outputs) if isinstance(outputs, dict) else {},
    }
    host_runtime = {
        "schema": AIE_HOST_RUNTIME_SCHEMA_ID,
        "entry": entry,
        "target": dict(package_manifest.get("target", {})),
        "mapping": json.loads(mapping_path.read_text()),
        "fifos": json.loads(fifos_path.read_text()),
    }

    (build_dir / "build_product.json").write_text(json.dumps(build_product, indent=2) + "\n")
    (build_dir / "host_runtime.json").write_text(json.dumps(host_runtime, indent=2) + "\n")
    return [
        "build/aie/build_product.json",
        "build/aie/host_runtime.json",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build HTP AIE reference toolchain outputs")
    parser.add_argument("--package", required=True, help="Path to the compiled HTP package")
    args = parser.parse_args()
    outputs = build_package(args.package)
    print(json.dumps({"built_outputs": outputs}, indent=2))


def _sha256_text(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    main()
