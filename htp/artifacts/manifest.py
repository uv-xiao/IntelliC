from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp.schemas import MANIFEST_SCHEMA_ID

from .validate import validate_manifest_graph


def write_manifest(
    package_dir: Path,
    *,
    current_stage: str,
    stages: list[dict[str, object]],
) -> dict[str, Any]:
    validate_manifest_graph(current_stage=current_stage, stages=stages)

    manifest = {
        "schema": MANIFEST_SCHEMA_ID,
        "stages": {
            "current": current_stage,
            "graph": stages,
        },
    }
    manifest_path = Path(package_dir) / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


__all__ = ["write_manifest"]
