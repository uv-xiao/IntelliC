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
        "ast_all_the_way.md",
        "artifacts_replay_debug.md",
        "backends_and_extensions.md",
        "compiler_model.md",
        "ir_infrastructure_review.md",
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
    docs_rules_text = Path(".agent/rules/docs-and-artifacts.md").read_text(encoding="utf-8")
    ast_design_text = Path("docs/design/ast_all_the_way.md").read_text(encoding="utf-8")
    ir_review_text = Path("docs/design/ir_infrastructure_review.md").read_text(encoding="utf-8")

    assert "Dialect features must compose across parse/capture" in agents_text
    assert "merge the final validated design from `docs/in_progress/design/`" in agents_text
    assert "active design drafts from `docs/in_progress/design/`" in docs_rules_text
    assert "Dialect features must compose through the shared substrate" in ast_design_text
    assert "IR infrastructure" in ir_review_text


def test_no_stale_in_progress_design_docs_when_no_active_tasks():
    in_progress_text = Path("docs/in_progress/README.md").read_text(encoding="utf-8")
    design_root = Path("docs/in_progress/design")

    if "## Active tasks\n\nNone." in in_progress_text:
        assert not list(design_root.glob("*.md"))
