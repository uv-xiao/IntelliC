def test_public_packages_import():
    import htp
    import htp.artifacts
    import htp.backends
    import htp.bindings
    import htp.compiler
    import htp.ir
    import htp.passes
    import htp.pipeline
    import htp.runtime
    import htp.solver
    import htp.tools

    assert htp.passes.__name__ == "htp.passes"
    assert htp.pipeline.__name__ == "htp.pipeline"
    assert htp.artifacts.__name__ == "htp.artifacts"
    assert htp.runtime.__name__ == "htp.runtime"
    assert htp.bindings.__name__ == "htp.bindings"
    assert htp.backends.__name__ == "htp.backends"
    assert htp.compiler.__name__ == "htp.compiler"
    assert htp.solver.__name__ == "htp.solver"
    assert htp.tools.__name__ == "htp.tools"


def test_schema_constants():
    from htp import schemas

    assert schemas.MANIFEST_SCHEMA_ID == "htp.manifest.v1"
    assert schemas.PASS_CONTRACT_SCHEMA_ID == "htp.pass_contract.v1"
    assert schemas.REPLAY_STUBS_SCHEMA_ID == "htp.replay.stubs.v1"
    assert schemas.ID_SCHEMA_IDS == {
        "entities": "htp.ids.entities.v1",
        "bindings": "htp.ids.bindings.v1",
    }
    assert schemas.MAP_SCHEMA_IDS == {
        "entity_map": "htp.entity_map.v1",
        "binding_map": "htp.binding_map.v1",
    }
