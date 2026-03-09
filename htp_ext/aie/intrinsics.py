from __future__ import annotations

from htp.intrinsics import IntrinsicDecl, register_handlers, register_intrinsic_package

AIE_INTRINSICS = (
    IntrinsicDecl(
        "aie.fifo_push",
        1,
        "backend",
        "channel_send",
        "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY",
        produces_effects=("protocol.fifo.pending_send",),
    ),
    IntrinsicDecl(
        "aie.fifo_pop",
        1,
        "backend",
        "channel_recv",
        "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY",
        discharges_effects=("protocol.fifo.pending_send",),
    ),
)

register_intrinsic_package("htp_ext.aie.intrinsics", AIE_INTRINSICS)
for intrinsic in AIE_INTRINSICS:
    register_handlers(
        "aie",
        intrinsic.name,
        lower=lambda *, op, target: dict(op, target=target),
        emit=lambda *, op, target: {"target": target, "intrinsic": op["intrinsic"]},
    )


__all__ = ["AIE_INTRINSICS"]
