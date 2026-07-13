"""atlas-badges CLI.

    atlas-badges scan  <path>   report detected concepts with evidence
    atlas-badges apply <path>   write the badge block into README.md

`scan` before `apply` is the intended workflow: read the evidence, decide
whether the detections are honest, correct with .atlas-concepts.yml, then
apply. The tool shows its working precisely so it can be distrusted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .badges import render_block
from .concepts import CATEGORIES, CONCEPTS_BY_ID
from .overrides import OVERRIDE_FILENAME, load_overrides, resolve
from .readme_writer import MarkerError, apply_to_readme
from .scanner import scan_repo

RULE = "-" * 64


def _validated_root(raw: str) -> Path:
    root = Path(raw)
    if not root.is_dir():
        print(f"error: {raw} is not a directory", file=sys.stderr)
        raise SystemExit(2)
    return root


def _print_warnings(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"  warning: {warning}", file=sys.stderr)


def cmd_scan(args: argparse.Namespace) -> int:
    root = _validated_root(args.path)
    detections = scan_repo(root)
    overrides = load_overrides(root)

    if args.json:
        payload = {
            "repo": str(root.resolve()),
            "detected": [
                {
                    "id": d.concept.id,
                    "name": d.concept.name,
                    "category": d.concept.category,
                    "total_matches": d.total_matches,
                    "evidence": [
                        {"path": e.path, "line": e.line, "text": e.text} for e in d.evidence
                    ],
                }
                for d in detections
            ],
            "overrides": {
                "found": overrides.found,
                "include": sorted(overrides.include),
                "exclude": sorted(overrides.exclude),
                "warnings": overrides.warnings,
            },
            "final": sorted(resolve({d.concept.id for d in detections}, overrides)),
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(RULE)
    print(f"atlas-badges scan · {root.resolve()}")
    print(RULE)

    if not detections:
        print("no concepts detected from static signals.")
    for det in detections:
        category = CATEGORIES[det.concept.category]["label"]
        extra = det.total_matches - len(det.evidence)
        suffix = f"  (+{extra} more match{'es' if extra != 1 else ''})" if extra > 0 else ""
        print(f"\n[{category}] {det.concept.name}{suffix}")
        for ev in det.evidence:
            location = f"{ev.path}:{ev.line}" if ev.line else ev.path
            print(f"    {location}  {ev.text}")

    print()
    if overrides.found:
        inc = ", ".join(sorted(overrides.include)) or "none"
        exc = ", ".join(sorted(overrides.exclude)) or "none"
        print(f"overrides ({OVERRIDE_FILENAME}): include [{inc}] · exclude [{exc}]")
    else:
        print(f"overrides: no {OVERRIDE_FILENAME} found")
    _print_warnings(overrides.warnings)

    final = resolve({d.concept.id for d in detections}, overrides)
    names = ", ".join(CONCEPTS_BY_ID[cid].name for cid in sorted(final)) or "none"
    print(f"final badge set ({len(final)}): {names}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    root = _validated_root(args.path)
    detections = scan_repo(root)
    overrides = load_overrides(root)
    _print_warnings(overrides.warnings)

    final = resolve({d.concept.id for d in detections}, overrides)
    block = render_block(final)

    if args.dry_run:
        print(block)

    try:
        action = apply_to_readme(root, block, dry_run=args.dry_run)
    except MarkerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    count = len(final)
    print(
        f"README.md {action} · {count} concept badge{'s' if count != 1 else ''}",
        file=sys.stderr if args.dry_run else sys.stdout,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlas-badges",
        description="Tag a repo's README with evidence-backed engineering concept badges.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="detect concepts and print the evidence")
    scan.add_argument("path", help="path to a local clone")
    scan.add_argument("--json", action="store_true", help="machine-readable output")
    scan.set_defaults(func=cmd_scan)

    apply_cmd = sub.add_parser("apply", help="write the badge block into README.md")
    apply_cmd.add_argument("path", help="path to a local clone")
    apply_cmd.add_argument(
        "--dry-run", action="store_true", help="print the block, touch nothing"
    )
    apply_cmd.set_defaults(func=cmd_apply)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
