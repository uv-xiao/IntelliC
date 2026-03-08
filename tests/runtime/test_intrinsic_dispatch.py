from __future__ import annotations

from htp.runtime.core import Runtime


def test_runtime_uses_registry_backed_intrinsic_simulation():
    runtime = Runtime()

    result = runtime.invoke_intrinsic(
        "portable.elementwise_binary",
        args=(2, 5),
        attrs={"operator": "add"},
        mode="sim",
    )

    assert result == 7
