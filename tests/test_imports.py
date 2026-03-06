import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_public_packages_import():
    import htp
    import htp.ir

    assert importlib.import_module("htp.pass").__name__ == "htp.pass"


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
