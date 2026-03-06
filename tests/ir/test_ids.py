import json

from htp.ir.ids import BindingRegistry, EntityRegistry, binding_id, entity_id, node_id


def test_entities_registry_is_deterministic():
    def build_payloads():
        entities = EntityRegistry("module::matmul_tile")
        loop_entity = entities.add("For", role="loop_k", node_kind="For", node_ordinal=7)
        mma_entity = entities.add("Call", role="mma", node_kind="Call", node_ordinal=31)

        bindings = BindingRegistry("module::matmul_tile")
        function_scope = bindings.add_scope("function")
        loop_scope = bindings.add_scope("for", parent=function_scope)
        loop_binding = bindings.add_binding(loop_scope, "k", site_entity_id=loop_entity)
        bindings.add_name_use("Name", 19, loop_binding)

        return entities.to_json(), bindings.to_json()

    first_entities, first_bindings = build_payloads()
    second_entities, second_bindings = build_payloads()

    assert node_id("module::matmul_tile", "For", 7) == "module::matmul_tile:For:7"
    assert entity_id("module::matmul_tile", 0) == "module::matmul_tile:E0"
    assert binding_id("module::matmul_tile:S1", 0) == "module::matmul_tile:S1:B0"

    assert first_entities == second_entities
    assert json.dumps(first_entities, sort_keys=False) == json.dumps(second_entities, sort_keys=False)
    assert first_entities == {
        "schema": "htp.ids.entities.v1",
        "def_id": "module::matmul_tile",
        "entities": [
            {"entity_id": "module::matmul_tile:E0", "kind": "For", "role": "loop_k"},
            {"entity_id": "module::matmul_tile:E1", "kind": "Call", "role": "mma"},
        ],
        "node_to_entity": [
            {"node_id": "module::matmul_tile:Call:31", "entity_id": "module::matmul_tile:E1"},
            {"node_id": "module::matmul_tile:For:7", "entity_id": "module::matmul_tile:E0"},
        ],
    }

    assert first_bindings == second_bindings
    assert first_bindings == {
        "schema": "htp.ids.bindings.v1",
        "def_id": "module::matmul_tile",
        "scopes": [
            {"scope_id": "module::matmul_tile:S0", "parent": None, "kind": "function"},
            {"scope_id": "module::matmul_tile:S1", "parent": "module::matmul_tile:S0", "kind": "for"},
        ],
        "bindings": [
            {
                "binding_id": "module::matmul_tile:S1:B0",
                "name": "k",
                "site_entity_id": "module::matmul_tile:E0",
            }
        ],
        "name_uses": [
            {"node_id": "module::matmul_tile:Name:19", "binding_id": "module::matmul_tile:S1:B0"}
        ],
    }
