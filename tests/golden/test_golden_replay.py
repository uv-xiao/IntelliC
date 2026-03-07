from tests.conftest import copy_golden_fixture

import htp


def test_golden_packages_replay_in_sim(tmp_path):
    expectations = {
        "pto_demo": ("s01", {"backend": "pto", "entry": "demo_kernel"}),
        "nvgpu_demo": ("s01", {"backend": "nvgpu", "entry": "demo_kernel", "profile": "nvidia:ampere:sm80"}),
    }

    for fixture_name, (stage_id, expected) in expectations.items():
        package_dir = copy_golden_fixture(fixture_name, tmp_path)
        session = htp.bind(package_dir).load(mode="sim")
        result = session.replay(stage_id)

        assert result.ok is True
        assert result.stage_id == stage_id
        assert result.result == expected
        assert result.diagnostics == []
        assert result.log_path is not None
