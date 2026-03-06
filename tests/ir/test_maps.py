from htp.ir.ids import BindingRegistry, EntityRegistry
from htp.ir.maps import BindingMap, EntityMap


def test_binding_map_records_split_and_introduced_bindings():
    entities = EntityRegistry("module::matmul")
    loop_entity = entities.add("For", role="loop_k", node_kind="For", node_ordinal=7)
    k0_entity = entities.add("For", role="loop_k0", node_kind="For", node_ordinal=8)
    k1_entity = entities.add("For", role="loop_k1", node_kind="For", node_ordinal=9)
    temp_entity = entities.add("Assign", role="pingpong_tmp", node_kind="Assign", node_ordinal=10)

    entity_map = EntityMap(pass_id="pkg::pass@1", stage_before="s06", stage_after="s07")
    entity_map.record(before=loop_entity, after=[k1_entity, k0_entity], reason="split_unrolled")
    entity_map.record(before=None, after=[temp_entity], reason="introduced_pingpong_buffer", origin=[loop_entity])

    bindings = BindingRegistry("module::matmul")
    function_scope = bindings.add_scope("function")
    before_scope = bindings.add_scope("for", parent=function_scope)
    after_scope = bindings.add_scope("for", parent=function_scope)
    old_binding = bindings.add_binding(before_scope, "k", site_entity_id=loop_entity)
    split_binding0 = bindings.add_binding(after_scope, "k0", site_entity_id=k0_entity)
    split_binding1 = bindings.add_binding(after_scope, "k1", site_entity_id=k1_entity)
    temp_binding = bindings.add_binding(after_scope, "tmp", site_entity_id=temp_entity)

    binding_map = BindingMap(pass_id="pkg::pass@1", stage_before="s06", stage_after="s07")
    binding_map.record(before=old_binding, after=[split_binding1, split_binding0], reason="split_unrolled")
    binding_map.record(before=None, after=[temp_binding], reason="introduced_temp", origin=[temp_entity])

    assert entity_map.to_json() == {
        "schema": "htp.entity_map.v1",
        "pass_id": "pkg::pass@1",
        "stage_before": "s06",
        "stage_after": "s07",
        "entities": [
            {
                "before": "module::matmul:E0",
                "after": ["module::matmul:E1", "module::matmul:E2"],
                "reason": "split_unrolled",
            },
            {
                "before": None,
                "after": ["module::matmul:E3"],
                "reason": "introduced_pingpong_buffer",
                "origin": ["module::matmul:E0"],
            },
        ],
    }

    assert binding_map.to_json() == {
        "schema": "htp.binding_map.v1",
        "pass_id": "pkg::pass@1",
        "stage_before": "s06",
        "stage_after": "s07",
        "bindings": [
            {
                "before": "module::matmul:S1:B0",
                "after": ["module::matmul:S2:B0", "module::matmul:S2:B1"],
                "reason": "split_unrolled",
            },
            {
                "before": None,
                "after": ["module::matmul:S2:B2"],
                "reason": "introduced_temp",
                "origin": ["module::matmul:E3"],
            },
        ],
    }
