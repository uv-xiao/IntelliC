from importlib.metadata import requires


def test_runtime_dependencies_include_numpy() -> None:
    requirements = requires("htp") or []
    assert any(requirement.startswith("numpy") for requirement in requirements)
