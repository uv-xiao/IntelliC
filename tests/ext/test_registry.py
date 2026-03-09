from __future__ import annotations

from htp_ext.registry import active_extensions, extension_results


def test_extension_registry_activates_requested_extension():
    program = {"extensions": {"requested": ["htp_ext.mlir_cse"]}}

    active = active_extensions(program)
    results = extension_results(program)

    assert [item.extension_id for item in active] == ["htp_ext.mlir_cse"]
    assert "htp_ext.mlir_cse" in results
