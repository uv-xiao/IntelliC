from __future__ import annotations

from .backend_ready_ir import run as run_backend_ready
from .core_ir import run as run_core
from .scheduled_ir import run as run_scheduled
from .surface_program import run as run_surface


def run_demo() -> dict[str, object]:
    return {
        "surface": run_surface(mode="sim"),
        "core": run_core(mode="sim"),
        "scheduled": run_scheduled(mode="sim"),
        "backend_ready": run_backend_ready(mode="sim"),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_demo(), indent=2))
