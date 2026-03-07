from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from htp.tools import explain_diagnostic, replay_package, semantic_diff, verify_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="htp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("package_dir")
    replay_parser.add_argument("--stage")
    replay_parser.add_argument("--entry")
    replay_parser.add_argument("--mode", default="sim")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("package_dir")
    verify_parser.add_argument("--goal", default="verify")
    verify_parser.add_argument("--mode", default="sim")

    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument("left_package_dir")
    diff_parser.add_argument("right_package_dir")
    diff_parser.add_argument("--semantic", action="store_true")
    diff_parser.add_argument("--left-stage")
    diff_parser.add_argument("--right-stage")

    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("code")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "replay":
        result = replay_package(
            args.package_dir,
            stage_id=args.stage,
            entry=args.entry,
            mode=args.mode,
        )
        print(json.dumps(_serialize_dataclass_like(result), indent=2))
        return 0 if result.ok else 1
    if args.command == "verify":
        result = verify_package(args.package_dir, goal=args.goal, mode=args.mode)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    if args.command == "diff":
        if not args.semantic:
            parser.error("Only --semantic diff is supported in v1.")
        result = semantic_diff(
            args.left_package_dir,
            args.right_package_dir,
            left_stage_id=args.left_stage,
            right_stage_id=args.right_stage,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["equal"] else 1
    if args.command == "explain":
        result = explain_diagnostic(args.code)
        print(json.dumps(result, indent=2))
        return 0
    parser.error(f"Unhandled command: {args.command}")
    return 2


def _serialize_dataclass_like(value: object) -> dict[str, object]:
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    raise TypeError(f"Unsupported replay payload type: {type(value)!r}")


if __name__ == "__main__":
    raise SystemExit(main())
