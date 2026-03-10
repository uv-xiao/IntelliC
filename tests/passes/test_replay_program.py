from __future__ import annotations

from htp.passes.program_model import snapshot_program
from htp.passes.replay_program import render_program_state_module


def test_render_program_state_module_emits_readable_bindings():
    program = {
        "entry": "gemm_tile",
        "kernel": {"name": "gemm_tile", "args": [], "ops": []},
        "workload": {"entry": "gemm_tile", "tasks": [], "channels": [], "dependencies": []},
        "target": {"backend": "nvgpu", "option": "ampere"},
    }

    rendered = render_program_state_module(program)

    assert '"""Readable staged Python snapshot for HTP replay and debugging."""' in rendered
    assert "ENTRY = 'gemm_tile'" in rendered
    assert "KERNEL = " in rendered
    assert "WORKLOAD = " in rendered
    assert "TARGET = " in rendered
    assert "def run(*args, **kwargs):" in rendered

    namespace: dict[str, object] = {}
    exec(rendered, namespace)
    assert namespace["run"]() == snapshot_program(program)


def test_render_program_state_module_handles_non_identifier_and_colliding_keys():
    program = {
        "a-b": {"value": 1},
        "a_b": {"value": 2},
        "123bad": {"value": 3},
    }

    rendered = render_program_state_module(program)

    assert "A_B = {'value': 1}" in rendered
    assert "A_B_1 = {'value': 2}" in rendered
    assert "FIELD_123BAD = {'value': 3}" in rendered

    namespace: dict[str, object] = {}
    exec(rendered, namespace)
    assert namespace["run"]() == snapshot_program(program)
