from __future__ import annotations

import os
import subprocess

REQUIRED_BASE = "htp/dev"
REQUIRED_PREFIX = "htp/feat-"
SUMMARY_PATH = "docs/todo/README.md"
SYNC_PREFIXES = ("htp/", "htp_ext/", "examples/", "docs/design/")


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name != "pull_request":
        print("Skipping PR policy check outside pull_request events.")
        return 0

    base_ref = os.environ.get("GITHUB_BASE_REF", "")
    head_ref = os.environ.get("GITHUB_HEAD_REF", "")
    errors: list[str] = []

    if base_ref != REQUIRED_BASE:
        errors.append(f"PR base must be '{REQUIRED_BASE}', got '{base_ref or '<missing>'}'.")
    if not head_ref.startswith(REQUIRED_PREFIX):
        errors.append(f"PR head branch must start with '{REQUIRED_PREFIX}', got '{head_ref or '<missing>'}'.")

    changed_files = _changed_files(base_ref)
    if _requires_todo_sync(changed_files):
        if SUMMARY_PATH not in changed_files:
            errors.append(f"Changes touching {', '.join(SYNC_PREFIXES)} must also update '{SUMMARY_PATH}'.")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("PR policy checks passed.")
    return 0


def _requires_todo_sync(changed_files: list[str]) -> bool:
    return any(path.startswith(prefix) for path in changed_files for prefix in SYNC_PREFIXES)


def _changed_files(base_ref: str) -> list[str]:
    target = f"origin/{base_ref}" if base_ref else "HEAD^"
    subprocess.run(["git", "fetch", "origin", base_ref], check=False, stdout=subprocess.DEVNULL)
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{target}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
