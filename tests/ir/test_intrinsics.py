from __future__ import annotations

import pytest

from htp.intrinsics import (
    IntrinsicDecl,
    backend_intrinsics,
    emit_intrinsic,
    get_intrinsic_decl,
    get_stub_diagnostic_code,
    has_handler,
    lower_intrinsic,
    portable_intrinsics,
    register_handlers,
    register_intrinsic,
    register_intrinsic_package,
    registered_intrinsic_packages,
    require_handler,
    resolve_handler,
    simulate_intrinsic,
)


def test_portable_intrinsic_registry_exposes_declared_contracts():
    decl = get_intrinsic_decl("portable.reduction_sum")

    assert decl.name == "portable.reduction_sum"
    assert decl.version == 1
    assert decl.portability == "portable"
    assert decl.stub_diagnostic == "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
    assert decl.produces_effects == ()
    assert any(item.name == "portable.reduction_sum" for item in portable_intrinsics())

    channel_send = get_intrinsic_decl("portable.channel_send")
    assert channel_send.requires_effects == ("protocol.free_slot",)
    assert channel_send.produces_effects == ("protocol.used_slot",)

    allreduce = get_intrinsic_decl("portable.allreduce")
    assert allreduce.requires_effects == ("collective.pending_allreduce",)
    assert allreduce.discharges_effects == ("collective.pending_allreduce", "collective.allreduce")


def test_backend_handler_availability_is_declared_per_target():
    assert has_handler("nvgpu", "portable.matmul", role="lower") is True
    assert has_handler("nvgpu", "portable.matmul", role="emit") is True
    assert has_handler("pto", "portable.matmul", role="lower") is False
    assert has_handler("pto", "portable.elementwise_binary", role="emit") is True


def test_require_handler_raises_contract_error_for_missing_backend_support():
    with pytest.raises(ValueError, match="HTP.INTRINSIC.MISSING_HANDLER"):
        require_handler("pto", "portable.matmul", role="lower")

    assert get_stub_diagnostic_code("portable.channel_send") == "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"


def test_intrinsic_registry_dispatches_registered_lower_and_simulate_handlers():
    register_intrinsic(
        IntrinsicDecl(
            "vendor.scale2",
            1,
            "backend",
            "scale2",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
        )
    )
    register_handlers(
        "demo",
        "vendor.scale2",
        lower=lambda *, op, target: {
            "target": target,
            "intrinsic": op["intrinsic"],
            "factor": 2,
        },
        emit=lambda *, op, target: {"target": target, "emitted": op["intrinsic"]},
        simulate=lambda *, args, attrs, mode, trace: args[0] * 2,
    )

    lowered = lower_intrinsic("demo", {"intrinsic": "vendor.scale2"})
    emitted = emit_intrinsic("demo", {"intrinsic": "vendor.scale2"})

    assert lowered == {"target": "demo", "intrinsic": "vendor.scale2", "factor": 2}
    assert emitted == {"target": "demo", "emitted": "vendor.scale2"}
    assert simulate_intrinsic("vendor.scale2", args=(7,), attrs={}, mode="sim", target="demo") == 14
    assert resolve_handler("demo", "vendor.scale2", role="lower") is not None


def test_intrinsic_packages_split_portable_and_backend_owned_sets():
    register_intrinsic_package(
        "htp_ext.demo.intrinsics",
        (
            IntrinsicDecl(
                "demo.backend_scale",
                1,
                "backend",
                "backend_scale",
                "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            ),
        ),
    )

    assert "htp.core.portable" in registered_intrinsic_packages()
    assert "htp_ext.demo.intrinsics" in registered_intrinsic_packages()
    assert any(item.name == "portable.matmul" for item in portable_intrinsics())
    assert any(item.name == "demo.backend_scale" for item in backend_intrinsics())
