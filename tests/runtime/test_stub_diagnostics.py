from typing import NoReturn, get_type_hints

import pytest

from htp.runtime import ReplayDiagnosticError, raise_stub


def test_raise_stub_produces_structured_diagnostic():
    with pytest.raises(ReplayDiagnosticError) as excinfo:
        raise_stub(
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            node_id="node.intrinsic.7",
            entity_id="demo.intrinsic",
            kind="intrinsic",
            artifact_ref="ir/stages/s01/replay/stubs.json",
            detail="No simulator registered for demo.intrinsic",
        )

    error = excinfo.value
    assert error.code == "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
    assert error.payload == {
        "node_id": "node.intrinsic.7",
        "entity_id": "demo.intrinsic",
        "kind": "intrinsic",
        "artifact_ref": "ir/stages/s01/replay/stubs.json",
        "detail": "No simulator registered for demo.intrinsic",
        "reason": "missing_simulator",
        "next_actions": [
            "Register a simulator for the intrinsic in the replay runtime.",
            "Route replay through an owning extension if simulation is toolchain-specific.",
        ],
    }
    assert error.fix_hints == (
        "Register a simulator for the intrinsic in the replay runtime.",
        "Route replay through an owning extension if simulation is toolchain-specific.",
    )
    assert "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC" in str(error)


def test_raise_stub_is_typed_as_non_returning():
    assert get_type_hints(raise_stub)["return"] is NoReturn
