from __future__ import annotations

from pathlib import Path


def test_docs_root_has_only_supported_entries():
    docs_root = Path("docs")
    assert docs_root.is_dir()

    entries = {path.name for path in docs_root.iterdir()}
    assert entries == {
        "design",
        "in_progress",
        "reference",
        "research",
        "story.md",
        "todo",
    }


def test_docs_root_does_not_contain_legacy_layout_dirs():
    docs_root = Path("docs")

    assert not (docs_root / "future").exists()
    assert not (docs_root / "examples").exists()
    assert not (docs_root / "plans").exists()


def test_design_tree_has_only_supported_top_level_entries():
    design_root = Path("docs/design")
    entries = {path.name for path in design_root.iterdir()}
    assert entries == {
        "README.md",
        "agent_product_and_workflow.md",
        "artifacts_replay_debug.md",
        "backends_and_extensions.md",
        "compiler_model.md",
        "littlekernel_ast_comparison.md",
        "pipeline_and_solver.md",
        "programming_surfaces.md",
        "status_and_alignment.md",
    }


def test_todo_tree_has_only_supported_top_level_entries():
    todo_root = Path("docs/todo")
    entries = {path.name for path in todo_root.iterdir()}
    assert entries == {"README.md", "alignment_and_product_gaps.md"}


def test_agent_and_design_docs_record_frontend_composability_rules():
    agents_text = Path("AGENTS.md").read_text(encoding="utf-8")
    core_rules_text = Path(".agent/rules/core-development.md").read_text(encoding="utf-8")
    frontend_design_text = Path("docs/in_progress/design/03_dialects_and_frontends.md").read_text(
        encoding="utf-8"
    )
    task_text = Path("docs/in_progress/028-ast-all-the-way-contracts.md").read_text(encoding="utf-8")

    assert "Dialect features must compose across parse/capture" in agents_text
    assert "Keep frontend AST handlers small and single-purpose" in core_rules_text
    assert "## Frontend composability rules" in frontend_design_text
    assert "the final frontend-definition substrate must enforce dialect composability" in task_text
