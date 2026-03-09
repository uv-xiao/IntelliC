from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(".github/scripts/check_pr_policy.py")
    spec = importlib.util.spec_from_file_location("check_pr_policy", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_requires_todo_sync_for_code_and_design_changes():
    module = _load_module()

    assert module._requires_todo_sync(["htp/tools.py"]) is True
    assert module._requires_todo_sync(["docs/design/features.md"]) is True
    assert module._requires_todo_sync(["examples/serving_routine/demo.py"]) is True


def test_does_not_require_todo_sync_for_unrelated_changes():
    module = _load_module()

    assert module._requires_todo_sync(["README.md"]) is False
    assert module._requires_todo_sync(["docs/todo/README.md"]) is False
    assert module._requires_todo_sync(["docs/todo/gap_checklist.md"]) is False
