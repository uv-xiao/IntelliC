#!/usr/bin/env python3
"""Validate the clean ICI repository harness shape."""

from __future__ import annotations

from pathlib import Path


APPROVED_DOCS_ENTRIES = {
    "README.md",
    "story.md",
    "design",
    "todo",
    "in_progress",
    "notes",
}

PROHIBITED_HARNESS_DIRS = (".codex", ".claude", ".opencode")


def _has_ignore_entry(gitignore_text: str, entry: str) -> bool:
    return any(line.strip() == entry for line in gitignore_text.splitlines())


def validate_repo(root: Path) -> list[str]:
    """Return policy errors for a repository root."""
    errors: list[str] = []

    if not (root / "AGENTS.md").is_file():
        errors.append("missing AGENTS.md")

    for path in (
        ".agents/rules",
        ".agents/skills",
        ".agents/agents",
        ".agents/templates",
    ):
        if not (root / path).is_dir():
            errors.append(f"missing {path}")

    for path in PROHIBITED_HARNESS_DIRS:
        if (root / path).exists():
            errors.append(f"prohibited harness directory exists: {path}")

    docs_root = root / "docs"
    if not docs_root.is_dir():
        errors.append("missing docs/")
    else:
        entries = {path.name for path in docs_root.iterdir()}
        unexpected_entries = entries - APPROVED_DOCS_ENTRIES
        missing_entries = APPROVED_DOCS_ENTRIES - entries
        if unexpected_entries:
            errors.append(f"unexpected docs entries: {sorted(unexpected_entries)}")
        if missing_entries:
            errors.append(f"missing docs entries: {sorted(missing_entries)}")

    if (root / "docs/reference").exists():
        errors.append("docs/reference must not exist; use docs/notes")
    if (root / "docs/research").exists():
        errors.append("docs/research must not exist; use docs/notes")
    if not (root / "docs/notes/README.md").is_file():
        errors.append("missing docs/notes/README.md")

    in_progress_readme = root / "docs/in_progress/README.md"
    design_root = root / "docs/in_progress/design"
    if in_progress_readme.is_file() and "## Active Tasks\n\nNone." in in_progress_readme.read_text(
        encoding="utf-8"
    ):
        stale_designs = sorted(design_root.glob("*.md")) if design_root.exists() else []
        if stale_designs:
            errors.append(
                "stale in-progress design docs exist with no active tasks: "
                + ", ".join(str(path.relative_to(root)) for path in stale_designs)
            )

    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        errors.append("missing .gitignore")
    else:
        gitignore_text = gitignore.read_text(encoding="utf-8")
        for entry in (".references/", ".repositories/"):
            if not _has_ignore_entry(gitignore_text, entry):
                errors.append(f".gitignore must include {entry}")

    return errors


def main() -> int:
    errors = validate_repo(Path.cwd())
    if errors:
        for error in errors:
            print(f"repo harness policy error: {error}")
        return 1
    print("repo harness policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
