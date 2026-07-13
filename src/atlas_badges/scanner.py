"""Repo scanner: walk a local clone, collect evidence per concept.

The design rule throughout: never assert without evidence. A detection is
a list of (file, line, matched text) tuples a human can eyeball, not a
boolean. If the evidence looks wrong, .atlas-concepts.yml exists to say so.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from .concepts import CONCEPTS, Concept, Signal

# Directories that are never source-of-truth for what a repo demonstrates.
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
    "coverage",
    ".wrangler",
    ".next",
    "target",
    "vendor",
}

# A generated README badge block must never be evidence for itself, or the
# tool bootstraps its own detections on the second run. The override file
# is skipped for the same reason: naming a concept in tool config is a
# human instruction, not code evidence.
SELF_MARKER = "ATLAS_CONCEPT_BADGES"
SKIP_FILES = {".atlas-concepts.yml"}

MAX_FILE_BYTES = 512 * 1024  # bigger than this is a build artefact, not code
MAX_EVIDENCE_PER_FILE = 3  # keep scan output readable; counts stay exact


@dataclass
class Evidence:
    path: str  # repo-relative, posix separators
    line: int  # 1-based; 0 means "the file's existence is the evidence"
    text: str


@dataclass
class Detection:
    concept: Concept
    evidence: list[Evidence] = field(default_factory=list)
    total_matches: int = 0


@dataclass(frozen=True)
class _CompiledSignal:
    concept: Concept
    signal: Signal
    regex: re.Pattern | None  # None for filename signals


def _compile_all() -> list[_CompiledSignal]:
    compiled: list[_CompiledSignal] = []
    for concept in CONCEPTS:
        for signal in concept.signals:
            if signal.filename:
                compiled.append(_CompiledSignal(concept, signal, None))
            else:
                flags = re.IGNORECASE if signal.ignorecase else 0
                compiled.append(_CompiledSignal(concept, signal, re.compile(signal.pattern, flags)))
    return compiled


def _globs_match(globs: tuple[str, ...] | None, relpath: str) -> bool:
    if globs is None:
        return True
    return any(fnmatch.fnmatch(relpath, glob) for glob in globs)


def _is_probably_binary(head: bytes) -> bool:
    return b"\x00" in head


def iter_text_files(root: Path):
    """Yield (absolute path, repo-relative posix path) for scannable files."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if rel_parts[-1] in SKIP_FILES:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            head = path.open("rb").read(8192)
        except OSError:
            continue
        if _is_probably_binary(head):
            continue
        yield path, "/".join(rel_parts)


def scan_repo(root: Path) -> list[Detection]:
    """Scan a repo, returning detections sorted for deterministic output."""
    root = root.resolve()
    compiled = _compile_all()
    detections: dict[str, Detection] = {}

    def detection_for(concept: Concept) -> Detection:
        return detections.setdefault(concept.id, Detection(concept=concept))

    for path, relpath in iter_text_files(root):
        filename_hits = [
            c for c in compiled if c.regex is None and fnmatch.fnmatch(relpath, c.signal.pattern)
        ]
        for hit in filename_hits:
            det = detection_for(hit.concept)
            det.total_matches += 1
            det.evidence.append(Evidence(relpath, 0, "(file present)"))

        # Group applicable regex signals by concept: a line is one piece of
        # evidence for a concept no matter how many of its patterns hit it.
        by_concept: dict[str, tuple[Concept, list[re.Pattern]]] = {}
        for cs in compiled:
            if cs.regex is None or not _globs_match(cs.signal.globs, relpath):
                continue
            by_concept.setdefault(cs.concept.id, (cs.concept, []))[1].append(cs.regex)
        if not by_concept:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        per_file_count: dict[str, int] = {}
        for lineno, line in enumerate(text.splitlines(), start=1):
            if SELF_MARKER in line:
                continue
            for concept_id, (concept, regexes) in by_concept.items():
                if not any(rx.search(line) for rx in regexes):
                    continue
                det = detection_for(concept)
                det.total_matches += 1
                per_file_count[concept_id] = per_file_count.get(concept_id, 0) + 1
                if per_file_count[concept_id] <= MAX_EVIDENCE_PER_FILE:
                    det.evidence.append(Evidence(relpath, lineno, line.strip()[:160]))

    from .concepts import sort_key

    return sorted(detections.values(), key=lambda d: sort_key(d.concept))
