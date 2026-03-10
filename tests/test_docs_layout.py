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
    }


def test_todo_tree_has_only_supported_top_level_entries():
    todo_root = Path("docs/todo")
    entries = {path.name for path in todo_root.iterdir()}
    assert entries == {"README.md", "programming_surfaces.md"}
