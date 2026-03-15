from __future__ import annotations

import numpy as np
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


def test_portable_intrinsic_simulation_covers_tensor_reference_ops():
    lhs = np.arange(6, dtype=np.float32).reshape(2, 3)
    rhs = np.arange(12, dtype=np.float32).reshape(3, 4)
    matrix = np.arange(6, dtype=np.float32).reshape(2, 3)

    matmul = simulate_intrinsic("portable.matmul", args=(lhs, rhs), attrs={}, mode="sim", target="nvgpu")
    broadcast = simulate_intrinsic(
        "portable.broadcast",
        args=(np.array([1.0, 2.0], dtype=np.float32),),
        attrs={"shape": (2, 2)},
        mode="sim",
        target="nvgpu",
    )
    transpose = simulate_intrinsic(
        "portable.transpose",
        args=(matrix,),
        attrs={"axes": (1, 0)},
        mode="sim",
        target="nvgpu",
    )
    reshaped = simulate_intrinsic(
        "portable.reshape",
        args=(matrix,),
        attrs={"shape": (3, 2)},
        mode="sim",
        target="nvgpu",
    )
    reduced = simulate_intrinsic(
        "portable.reduction_sum",
        args=(matrix,),
        attrs={"axis": 0},
        mode="sim",
        target="nvgpu",
    )

    assert np.array_equal(matmul, lhs @ rhs)
    assert np.array_equal(broadcast, np.broadcast_to(np.array([1.0, 2.0], dtype=np.float32), (2, 2)))
    assert np.array_equal(transpose, matrix.T)
    assert np.array_equal(reshaped, matrix.reshape(3, 2))
    assert np.array_equal(reduced, matrix.sum(axis=0))


def test_portable_slice_simulation_supports_symbolic_full_extent_sizes():
    source = np.arange(24, dtype=np.float32).reshape(2, 12)

    sliced = simulate_intrinsic(
        "portable.slice",
        args=(source,),
        attrs={
            "offsets": (0, 4),
            "sizes": ("M", 4),
            "offset_exprs": ("0", "warp_stage * 4"),
            "size_exprs": ("M", "4"),
        },
        mode="sim",
        target="nvgpu",
    )

    assert np.array_equal(sliced, source[:, 4:8])


def test_portable_intrinsic_simulation_covers_async_and_mma_reference_ops():
    lhs = np.arange(6, dtype=np.float32).reshape(2, 3)
    rhs = np.arange(6, dtype=np.float32).reshape(3, 2)
    accum = np.ones((2, 2), dtype=np.float32)

    copied = simulate_intrinsic(
        "portable.async_copy",
        args=(lhs,),
        attrs={"memory_space": "shared"},
        mode="sim",
        target="nvgpu",
    )
    waited = simulate_intrinsic(
        "portable.await",
        args=(copied,),
        attrs={},
        mode="sim",
        target="nvgpu",
    )
    mma = simulate_intrinsic(
        "portable.mma",
        args=(lhs, rhs, accum),
        attrs={},
        mode="sim",
        target="nvgpu",
    )
    allreduce = simulate_intrinsic(
        "portable.allreduce",
        args=(accum,),
        attrs={"participants": 1},
        mode="sim",
        target="nvgpu",
    )

    assert np.array_equal(copied, lhs)
    assert copied is not lhs
    assert np.array_equal(waited, lhs)
    assert np.array_equal(mma, lhs @ rhs + accum)
    assert np.array_equal(allreduce, accum)
