#!/usr/bin/env python3
"""Record human instructions under docs/in_progress/human_words/."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from pathlib import Path


TIMELINE_HEADING = "## Timeline"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug) or "other"


def read_instruction(args: argparse.Namespace) -> str:
    if args.instruction_file:
        return Path(args.instruction_file).read_text(encoding="utf-8").strip()
    if args.instruction:
        return args.instruction.strip()
    raise SystemExit("Either --instruction or --instruction-file is required.")


def blockquote(text: str) -> str:
    lines = text.splitlines() or [""]
    return "\n".join(f"  > {line}" for line in lines)


def entry_sort_key(entry: str, index: int) -> tuple[str, int]:
    first_line = entry.splitlines()[0] if entry.splitlines() else ""
    match = re.match(r"- (\d{4}-\d{2}-\d{2})(?: ([0-9]{2}:[0-9]{2}))?", first_line)
    timestamp = match.group(1) + " " + (match.group(2) or "00:00") if match else "9999-99-99 99:99"
    return timestamp, index


def split_entries(timeline_body: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    for line in timeline_body.strip().splitlines():
        if line.startswith("- ") and current:
            entries.append("\n".join(current).rstrip())
            current = [line]
        elif line.startswith("- "):
            current = [line]
        elif current:
            current.append(line)
    if current:
        entries.append("\n".join(current).rstrip())
    return entries


def render_file(category: str, entries: list[str]) -> str:
    sorted_entries = [
        entry
        for _, entry in sorted(
            ((entry_sort_key(entry, index), entry) for index, entry in enumerate(entries)),
            key=lambda item: item[0],
        )
    ]
    timeline = "\n\n".join(sorted_entries)
    return (
        f"# Human Words: {category}\n\n"
        "## Category\n\n"
        f"- Primary: {category}\n\n"
        f"{TIMELINE_HEADING}\n\n"
        f"{timeline}\n"
    )


def load_entries(path: Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    if TIMELINE_HEADING not in content:
        return []
    return split_entries(content.split(TIMELINE_HEADING, 1)[1])


def build_entry(args: argparse.Namespace, instruction: str) -> str:
    timestamp = args.timestamp
    if not timestamp:
        now = dt.datetime.now().astimezone()
        timestamp = now.strftime("%Y-%m-%d %H:%M")
    timezone = args.timezone or os.environ.get("TZ") or "local"
    lines = [f"- {timestamp} {timezone} - {args.event}", blockquote(instruction)]
    if args.context:
        lines.append(f"  - Context: {args.context}")
    for related in args.related:
        lines.append(f"  - Related: {related}")
    if args.interpretation:
        lines.append(f"  - Agent interpretation: {args.interpretation}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--category", required=True, help="Category name, for example 'Agent Harness'.")
    parser.add_argument("--event", required=True, help="Short timeline event label.")
    parser.add_argument("--instruction", help="Exact human instruction text.")
    parser.add_argument("--instruction-file", help="File containing exact human instruction text.")
    parser.add_argument("--context", default="", help="Conversation or task context.")
    parser.add_argument("--related", action="append", default=[], help="Related file or document. Repeat as needed.")
    parser.add_argument("--interpretation", default="", help="Non-normative agent interpretation.")
    parser.add_argument("--timestamp", help="Timestamp in 'YYYY-MM-DD HH:MM' form. Defaults to now.")
    parser.add_argument("--timezone", help="Timezone label. Defaults to TZ or 'local'.")
    parser.add_argument("--output", help="Override output file path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruction = read_instruction(args)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output) if args.output else (
        repo_root / "docs" / "in_progress" / "human_words" / f"{slugify(args.category)}.md"
    )
    if not output.is_absolute():
        output = repo_root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    entries = load_entries(output)
    entries.append(build_entry(args, instruction))
    output.write_text(render_file(args.category, entries), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
