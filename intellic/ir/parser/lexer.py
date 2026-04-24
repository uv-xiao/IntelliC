from __future__ import annotations


def strip_comments(text: str) -> str:
    """Remove line comments from canonical test input."""

    return "\n".join(line.split("//", 1)[0].rstrip() for line in text.splitlines())
