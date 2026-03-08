from __future__ import annotations

import pytest

from htp.intrinsics import (
    get_intrinsic_decl,
    get_stub_diagnostic_code,
    has_handler,
    require_handler,
)


def test_portable_intrinsic_registry_exposes_declared_contracts():
    decl = get_intrinsic_decl("portable.reduction_sum")

    assert decl.name == "portable.reduction_sum"
    assert decl.version == 1
    assert decl.portability == "portable"
    assert decl.stub_diagnostic == "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
    assert decl.produces_effects == ()


def test_backend_handler_availability_is_declared_per_target():
    assert has_handler("nvgpu", "portable.matmul", role="lower") is True
    assert has_handler("nvgpu", "portable.matmul", role="emit") is True
    assert has_handler("pto", "portable.matmul", role="lower") is False
    assert has_handler("pto", "portable.elementwise_binary", role="emit") is True


def test_require_handler_raises_contract_error_for_missing_backend_support():
    with pytest.raises(ValueError, match="HTP.INTRINSIC.MISSING_HANDLER"):
        require_handler("pto", "portable.matmul", role="lower")

    assert get_stub_diagnostic_code("portable.channel_send") == "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
