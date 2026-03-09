"""Schema identifiers referenced by the HTP design docs."""

MANIFEST_SCHEMA_ID = "htp.manifest.v1"
PASS_CONTRACT_SCHEMA_ID = "htp.pass_contract.v1"
REPLAY_STUBS_SCHEMA_ID = "htp.replay.stubs.v1"
BINDING_LOG_SCHEMA_ID = "htp.binding_log.v1"
PERF_SCHEMA_ID = "htp.perf.v1"

IDS_ENTITIES_SCHEMA_ID = "htp.ids.entities.v1"
IDS_BINDINGS_SCHEMA_ID = "htp.ids.bindings.v1"
ENTITY_MAP_SCHEMA_ID = "htp.entity_map.v1"
BINDING_MAP_SCHEMA_ID = "htp.binding_map.v1"

ID_SCHEMA_IDS = {
    "entities": IDS_ENTITIES_SCHEMA_ID,
    "bindings": IDS_BINDINGS_SCHEMA_ID,
}

MAP_SCHEMA_IDS = {
    "entity_map": ENTITY_MAP_SCHEMA_ID,
    "binding_map": BINDING_MAP_SCHEMA_ID,
}

__all__ = [
    "BINDING_MAP_SCHEMA_ID",
    "BINDING_LOG_SCHEMA_ID",
    "ENTITY_MAP_SCHEMA_ID",
    "IDS_BINDINGS_SCHEMA_ID",
    "IDS_ENTITIES_SCHEMA_ID",
    "ID_SCHEMA_IDS",
    "MANIFEST_SCHEMA_ID",
    "MAP_SCHEMA_IDS",
    "PASS_CONTRACT_SCHEMA_ID",
    "PERF_SCHEMA_ID",
    "REPLAY_STUBS_SCHEMA_ID",
]
