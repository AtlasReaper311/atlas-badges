"""Per-repo overrides: .atlas-concepts.yml

Static scanning has limits. A concept can be real but documented only in
prose (force-include it), or a pattern can match something that is not
actually the concept (force-exclude it). This file exists so the tool
never asserts something false with high confidence; it admits the limits
of grepping instead of papering over them.

Schema, both keys optional:

    include:
      - rag-vector-search
    exclude:
      - kv-caching

Unknown concept ids produce a warning, never a crash: a stale override
should degrade to an honest note, not break a scan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .concepts import CONCEPTS_BY_ID

OVERRIDE_FILENAME = ".atlas-concepts.yml"


@dataclass
class Overrides:
    include: set[str] = field(default_factory=set)
    exclude: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    found: bool = False


def _clean_id_list(raw, key: str, warnings: list[str]) -> set[str]:
    if raw is None:
        return set()
    if not isinstance(raw, list):
        warnings.append(f"'{key}' should be a list of concept ids; ignoring it")
        return set()
    ids: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            warnings.append(f"'{key}' contains a non-string entry ({item!r}); skipped")
            continue
        concept_id = item.strip()
        if concept_id not in CONCEPTS_BY_ID:
            warnings.append(f"unknown concept id '{concept_id}' in '{key}'; skipped")
            continue
        ids.add(concept_id)
    return ids


def load_overrides(repo_root: Path) -> Overrides:
    path = repo_root / OVERRIDE_FILENAME
    if not path.is_file():
        return Overrides()

    warnings: list[str] = []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return Overrides(
            warnings=[f"couldn't parse {OVERRIDE_FILENAME}: {exc}; ignoring overrides"],
            found=True,
        )

    if raw is None:
        return Overrides(found=True)
    if not isinstance(raw, dict):
        return Overrides(
            warnings=[f"{OVERRIDE_FILENAME} should be a mapping; ignoring overrides"],
            found=True,
        )

    include = _clean_id_list(raw.get("include"), "include", warnings)
    exclude = _clean_id_list(raw.get("exclude"), "exclude", warnings)

    both = include & exclude
    for concept_id in sorted(both):
        warnings.append(
            f"'{concept_id}' is in both include and exclude; exclude wins (the safer read)"
        )
    include -= both

    return Overrides(include=include, exclude=exclude, warnings=warnings, found=True)


def resolve(detected_ids: set[str], overrides: Overrides) -> set[str]:
    """Final concept set: (detected + forced in) - forced out."""
    return (detected_ids | overrides.include) - overrides.exclude
