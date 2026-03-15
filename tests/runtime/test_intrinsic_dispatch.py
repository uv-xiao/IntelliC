from __future__ import annotations

import numpy as np
import pytest

from htp.runtime import ReplayDiagnosticError
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


def test_runtime_channel_intrinsics_use_runtime_queue():
    runtime = Runtime()

    sent = runtime.invoke_intrinsic(
        "portable.channel_send",
        args=(11,),
        attrs={"channel": "tiles"},
        mode="sim",
    )
    received = runtime.invoke_intrinsic(
        "portable.channel_recv",
        args=(),
        attrs={"channel": "tiles"},
        mode="sim",
    )

    assert sent == 11
    assert received == 11


def test_runtime_channel_recv_reports_empty_queue_without_stub_wrapping():
    runtime = Runtime()

    with pytest.raises(ReplayDiagnosticError) as excinfo:
        runtime.invoke_intrinsic(
            "portable.channel_recv",
            args=(),
            attrs={"channel": "tiles"},
            mode="sim",
        )

    assert excinfo.value.code == "HTP.REPLAY.STUB_HIT"
    assert excinfo.value.payload["detail"] == "channel 'tiles' is empty in sim replay"


def test_runtime_slice_intrinsic_accepts_symbolic_extent_sizes():
    runtime = Runtime()

    result = runtime.invoke_intrinsic(
        "portable.slice",
        args=(np.arange(8, dtype=np.float32).reshape(2, 4),),
        attrs={
            "offsets": (0, 1),
            "sizes": ("rows", 2),
            "offset_exprs": ("0", "stage * 2"),
            "size_exprs": ("rows", "2"),
        },
        mode="sim",
    )

    assert np.array_equal(result, np.array([[1, 2], [5, 6]], dtype=np.float32))
