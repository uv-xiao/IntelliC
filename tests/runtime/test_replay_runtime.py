from types import ModuleType

import htp.runtime as runtime_api


class RecordingRuntime:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def call_kernel(self, kernel_id, *, args, mode, artifacts, trace=None):
        event = {
            "kernel_id": kernel_id,
            "args": args,
            "mode": mode,
            "artifacts": artifacts,
            "trace": trace,
        }
        self.events.append(("kernel", event))
        return ("kernel", kernel_id, args, mode)

    def invoke_intrinsic(self, name, *, args, attrs=None, mode, trace=None):
        event = {
            "name": name,
            "args": args,
            "attrs": attrs,
            "mode": mode,
            "trace": trace,
        }
        self.events.append(("intrinsic", event))
        return ("intrinsic", name, attrs)

    def invoke_extension(self, extension_id, operation, *, payload, mode, trace=None):
        event = {
            "extension_id": extension_id,
            "operation": operation,
            "payload": payload,
            "mode": mode,
            "trace": trace,
        }
        self.events.append(("extension", event))
        return ("extension", extension_id, operation, payload["kwargs"])


def test_stage_run_defaults_to_default_runtime(monkeypatch):
    runtime = RecordingRuntime()
    monkeypatch.setattr(runtime_api, "default_runtime", lambda: runtime)

    module = ModuleType("generated_stage")
    exec(
        """
import htp.runtime as runtime_api

STAGE_INFO = {
    "stage_id": "s01",
    "def_id": "demo::stage@1",
    "runnable_py": "preserves",
    "supported_modes": ("sim",),
}


def run(*args, mode="sim", runtime=None, trace=None, **kwargs):
    runtime = runtime_api.default_runtime() if runtime is None else runtime
    kernel = runtime_api.call_kernel(
        "demo.kernel",
        args=args,
        mode=mode,
        artifacts={"program": "ir/stages/s01/program.py"},
        trace=trace,
        runtime=runtime,
    )
    intrinsic = runtime_api.intrinsics.invoke(
        "demo.intrinsic",
        args=args,
        attrs={"scale": 2},
        mode=mode,
        trace=trace,
        runtime=runtime,
    )
    extension = runtime_api.extensions.invoke(
        "demo.ext",
        "fold",
        payload={"args": args, "kwargs": kwargs},
        mode=mode,
        trace=trace,
        runtime=runtime,
    )
    return kernel, intrinsic, extension
""",
        module.__dict__,
    )

    result = module.run(1, 2, trace={"kind": "basic"}, flag=True)

    assert result == (
        ("kernel", "demo.kernel", (1, 2), "sim"),
        ("intrinsic", "demo.intrinsic", {"scale": 2}),
        ("extension", "demo.ext", "fold", {"flag": True}),
    )
    assert runtime.events == [
        (
            "kernel",
            {
                "kernel_id": "demo.kernel",
                "args": (1, 2),
                "mode": "sim",
                "artifacts": {"program": "ir/stages/s01/program.py"},
                "trace": {"kind": "basic"},
            },
        ),
        (
            "intrinsic",
            {
                "name": "demo.intrinsic",
                "args": (1, 2),
                "attrs": {"scale": 2},
                "mode": "sim",
                "trace": {"kind": "basic"},
            },
        ),
        (
            "extension",
            {
                "extension_id": "demo.ext",
                "operation": "fold",
                "payload": {"args": (1, 2), "kwargs": {"flag": True}},
                "mode": "sim",
                "trace": {"kind": "basic"},
            },
        ),
    ]
