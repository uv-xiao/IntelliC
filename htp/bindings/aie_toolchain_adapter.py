from __future__ import annotations

import importlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from htp.schemas import ADAPTER_TRACE_SCHEMA_ID


def build_package(
    package_dir: Path,
    manifest: dict[str, Any],
    *,
    mode: str,
    force: bool,
) -> tuple[list[str], list[dict[str, Any]], str | None]:
    del force
    try:
        toolchain_manifest = json.loads((package_dir / "codegen" / "aie" / "toolchain.json").read_text())
        driver = toolchain_manifest["build_driver"]
        module = importlib.import_module(str(driver["module"]))
        callable_name = str(driver["callable"])
        built_outputs = list(getattr(module, callable_name)(package_dir, manifest))
    except Exception as exc:
        trace_ref = _write_adapter_trace(
            package_dir,
            action="build",
            payload={"ok": False, "mode": mode, "exception_type": exc.__class__.__name__, "detail": str(exc)},
        )
        return [], [{"code": "HTP.BINDINGS.AIE_BUILD_ERROR", "detail": str(exc), "mode": mode}], trace_ref
    trace_ref = _write_adapter_trace(
        package_dir,
        action="build",
        payload={"ok": True, "mode": mode, "built_outputs": built_outputs},
    )
    return built_outputs, [], trace_ref


def run_package(
    package_dir: Path,
    manifest: dict[str, Any],
    *,
    mode: str,
    entry: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> tuple[bool, Any, list[dict[str, Any]], str | None]:
    host_path = package_dir / "codegen" / "aie" / "host.py"
    build_runtime_path = package_dir / "build" / "aie" / "host_runtime.json"
    if mode == "device" and not build_runtime_path.exists():
        trace_ref = _write_adapter_trace(
            package_dir,
            action="run",
            payload={"ok": False, "mode": mode, "detail": "missing build/aie/host_runtime.json"},
        )
        return (
            False,
            None,
            [
                {
                    "code": "HTP.BINDINGS.AIE_RUN_ERROR",
                    "detail": "AIE device run requires build/aie/host_runtime.json. Run build(mode='device') first.",
                    "mode": mode,
                }
            ],
            trace_ref,
        )
    try:
        module = _load_python_module(host_path, module_name="htp_aie_host_launch")
        result = module.launch(
            *args,
            package_dir=package_dir.as_posix(),
            build_dir=(package_dir / "build" / "aie").as_posix(),
            entry=entry,
            mode=mode,
            **kwargs,
        )
    except Exception as exc:
        trace_ref = _write_adapter_trace(
            package_dir,
            action="run",
            payload={"ok": False, "mode": mode, "entry": entry, "detail": str(exc)},
        )
        return (
            False,
            None,
            [{"code": "HTP.BINDINGS.AIE_RUN_ERROR", "detail": str(exc), "mode": mode, "entry": entry}],
            trace_ref,
        )
    trace_ref = _write_adapter_trace(
        package_dir,
        action="run",
        payload={"ok": True, "mode": mode, "entry": entry},
    )
    return True, result, [], trace_ref


def _write_adapter_trace(package_dir: Path, *, action: str, payload: dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    relative_path = Path("logs") / f"adapter_aie_{action}_{timestamp}_{uuid4().hex[:8]}.json"
    trace_path = package_dir / relative_path
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "schema": ADAPTER_TRACE_SCHEMA_ID,
                "backend": "aie",
                "adapter": "reference-toolchain",
                "action": action,
                "payload": payload,
            },
            indent=2,
        )
        + "\n"
    )
    return relative_path.as_posix()


def _load_python_module(module_path: Path, *, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Python module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
