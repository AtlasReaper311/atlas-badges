"""README splicing: put the badge block in without touching anything else.

Rules:
  markers present   -> replace only what sits between them
  no markers        -> insert after the first H1 (badges belong under the
                       title, not buried at the bottom), else prepend
  no README at all  -> create a minimal one and say so

Re-running against an already correct README is byte-identical, so callers
can diff-before-write and CI can run this without generating noise commits.
"""

from __future__ import annotations

from pathlib import Path

from .badges import END_MARKER, START_MARKER


class MarkerError(ValueError):
    """Markers exist but are malformed (END before START, or only one)."""


def splice(existing: str, block: str) -> str:
    has_start = START_MARKER in existing
    has_end = END_MARKER in existing

    if has_start != has_end:
        missing = END_MARKER if has_start else START_MARKER
        raise MarkerError(f"found one badge marker but not {missing}; fix the README first")

    if has_start:
        start = existing.index(START_MARKER)
        end = existing.index(END_MARKER)
        if end < start:
            raise MarkerError("badge END marker appears before START; fix the README first")
        return existing[:start] + block + existing[end + len(END_MARKER):]

    lines = existing.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.lstrip().startswith("# "):
            insert_at = i + 1
            prefix = "".join(lines[:insert_at])
            suffix = "".join(lines[insert_at:])
            if not prefix.endswith("\n"):
                prefix += "\n"
            return f"{prefix}\n{block}\n{suffix}"

    sep = "\n\n" if existing.strip() else "\n"
    return f"{block}{sep}{existing}"


def apply_to_readme(repo_root: Path, block: str, dry_run: bool = False) -> str:
    """Write the block into <repo>/README.md.

    Returns one of: "created", "updated", "unchanged" (plus "would-*"
    variants under dry_run). Only writes when bytes actually change; the
    same only-signal-genuine-change rule the rest of the estate follows.
    """
    readme = repo_root / "README.md"

    if not readme.exists():
        content = f"# {repo_root.resolve().name}\n\n{block}\n"
        if dry_run:
            return "would-create"
        readme.write_text(content, encoding="utf-8")
        return "created"

    existing = readme.read_text(encoding="utf-8")
    updated = splice(existing, block)

    if updated == existing:
        return "unchanged"
    if dry_run:
        return "would-update"
    readme.write_text(updated, encoding="utf-8")
    return "updated"
