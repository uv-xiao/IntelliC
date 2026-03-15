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
    assert module._requires_todo_sync(["docs/design/compiler_model.md"]) is True
    assert module._requires_todo_sync(["examples/serving_routine/demo.py"]) is True


def test_does_not_require_todo_sync_for_unrelated_changes():
    module = _load_module()

    assert module._requires_todo_sync(["README.md"]) is False
    assert module._requires_todo_sync(["docs/todo/README.md"]) is False
    assert module._requires_todo_sync(["docs/todo/compiler_model.md"]) is False


def test_agent_policy_requires_corridor_docs_and_tests():
    module = _load_module()

    report = module.evaluate_edit_policy(["htp/agent_policy.py"])

    assert report["ok"] is False
    assert "tests/tools" in report["missing_required_tests"]
    assert "docs/design/agent_product_and_workflow.md" in report["missing_required_docs"]


def test_agent_policy_allows_example_edits_within_global_roots():
    module = _load_module()

    report = module.evaluate_edit_policy(["examples/wsp_warp_gemm/demo.py"])

    assert "examples/wsp_warp_gemm/demo.py" not in report["root_violations"]


def test_agent_policy_passes_when_workflow_corridor_is_satisfied():
    module = _load_module()

    report = module.evaluate_edit_policy(
        [
            "htp/agent_policy.py",
            "htp/tools.py",
            "tests/tools/test_tools.py",
            "tests/test_pr_policy_script.py",
            "docs/design/agent_product_and_workflow.md",
            "docs/todo/README.md",
            "AGENTS.md",
        ]
    )

    assert report["ok"] is True
    assert [template["name"] for template in report["active_templates"]] == ["agent_workflow"]
