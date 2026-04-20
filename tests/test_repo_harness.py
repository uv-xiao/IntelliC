from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_repo_harness import validate_repo


def write_file(root: Path, path: str, content: str = "") -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def create_valid_repo(root: Path) -> None:
    write_file(root, ".gitignore", ".references/\n.repositories/\n")
    write_file(root, "AGENTS.md", "# Agent Guide\n")
    for path in (
        ".agents/rules/README.md",
        ".agents/skills/README.md",
        ".agents/agents/README.md",
        ".agents/templates/README.md",
        "docs/README.md",
        "docs/story.md",
        "docs/design/README.md",
        "docs/todo/README.md",
        "docs/in_progress/README.md",
        "docs/notes/README.md",
    ):
        write_file(root, path, "# file\n")
    write_file(root, "docs/in_progress/README.md", "# In Progress\n\n## Active Tasks\n\nNone.\n")


class RepoHarnessPolicyTests(unittest.TestCase):
    def test_clean_scaffold_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_valid_repo(root)

            self.assertEqual(validate_repo(root), [])

    def test_prohibited_harness_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_valid_repo(root)
            (root / ".codex").mkdir()

            self.assertIn("prohibited harness directory exists: .codex", validate_repo(root))

    def test_stale_in_progress_design_fails_when_no_active_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_valid_repo(root)
            write_file(root, "docs/in_progress/design/stale.md", "# stale\n")

            errors = validate_repo(root)

            self.assertTrue(any("stale in-progress design docs" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
