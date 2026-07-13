"""Tests for overrides, badge rendering, and README splicing."""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas_badges.badges import (
    END_MARKER,
    START_MARKER,
    badge_url,
    render_block,
)
from atlas_badges.overrides import load_overrides, resolve
from atlas_badges.readme_writer import (
    MarkerError,
    apply_to_readme,
    splice,
)

# --------------------------------------------------------------- overrides


def test_missing_override_file_is_empty(tmp_path: Path) -> None:
    overrides = load_overrides(tmp_path)
    assert not overrides.found
    assert overrides.include == set() and overrides.exclude == set()


def test_include_and_exclude_are_applied(tmp_path: Path) -> None:
    (tmp_path / ".atlas-concepts.yml").write_text(
        "include:\n  - rag-vector-search\nexclude:\n  - kv-caching\n",
        encoding="utf-8",
    )
    overrides = load_overrides(tmp_path)
    final = resolve({"kv-caching", "hmac-verification"}, overrides)
    assert final == {"hmac-verification", "rag-vector-search"}


def test_unknown_ids_warn_but_never_crash(tmp_path: Path) -> None:
    (tmp_path / ".atlas-concepts.yml").write_text(
        "include:\n  - not-a-real-concept\n", encoding="utf-8"
    )
    overrides = load_overrides(tmp_path)
    assert overrides.include == set()
    assert any("not-a-real-concept" in w for w in overrides.warnings)


def test_conflicting_entry_resolves_to_exclude(tmp_path: Path) -> None:
    (tmp_path / ".atlas-concepts.yml").write_text(
        "include:\n  - kv-caching\nexclude:\n  - kv-caching\n", encoding="utf-8"
    )
    overrides = load_overrides(tmp_path)
    assert resolve({"kv-caching"}, overrides) == set()
    assert overrides.warnings


def test_malformed_yaml_degrades_to_no_overrides(tmp_path: Path) -> None:
    (tmp_path / ".atlas-concepts.yml").write_text("include: [unclosed", encoding="utf-8")
    overrides = load_overrides(tmp_path)
    assert overrides.include == set() and overrides.exclude == set()
    assert overrides.warnings


# ------------------------------------------------------------------ badges


def test_badge_url_escaping() -> None:
    url = badge_url("infra", "KV caching with TTL", "f5a623")
    assert "KV_caching_with_TTL" in url
    assert "labelColor=0a0a0f" in url and "style=flat-square" in url

    slashed = badge_url("data", "RAG / vector search", "e8e8e0")
    assert "RAG_%2F_vector_search" in slashed
    assert "/" not in slashed.split("/badge/")[1]  # spec is one path segment

    assert "HMAC--like" in badge_url("security", "HMAC-like", "f5a623")


def test_render_block_is_deterministic_and_ordered() -> None:
    ids = {"kv-caching", "hmac-verification", "reusable-ci"}
    block_a = render_block(ids)
    block_b = render_block(set(sorted(ids)))
    assert block_a == block_b
    # security before infra before ci, per category order
    assert block_a.index("HMAC") < block_a.index("KV_caching") < block_a.index("Reusable")


# ---------------------------------------------------------------- splicing


def test_splice_inserts_after_title() -> None:
    readme = "# my-repo\n\nSome hand-written intro.\n"
    result = splice(readme, render_block({"kv-caching"}))
    assert result.startswith("# my-repo\n\n<!-- ATLAS_CONCEPT_BADGES:START -->")
    assert "Some hand-written intro." in result


def test_splice_replaces_between_markers_only() -> None:
    readme = (
        "# repo\n\nintro stays\n\n"
        f"{START_MARKER}\nOLD CONTENT\n{END_MARKER}\n\noutro stays\n"
    )
    result = splice(readme, render_block({"hmac-verification"}))
    assert "OLD CONTENT" not in result
    assert "intro stays" in result and "outro stays" in result
    assert result.count(START_MARKER) == 1 and result.count(END_MARKER) == 1


def test_splice_rejects_broken_markers() -> None:
    with pytest.raises(MarkerError):
        splice(f"# x\n{START_MARKER}\nno end\n", "block")
    with pytest.raises(MarkerError):
        splice(f"# x\n{END_MARKER}\nbackwards\n{START_MARKER}\n", "block")


def test_apply_is_idempotent(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# demo\n\nhand-written text.\n", encoding="utf-8")
    block = render_block({"kv-caching", "hmac-verification"})

    assert apply_to_readme(tmp_path, block) == "updated"
    first_pass = (tmp_path / "README.md").read_text(encoding="utf-8")

    assert apply_to_readme(tmp_path, block) == "unchanged"
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == first_pass


def test_apply_creates_readme_when_missing(tmp_path: Path) -> None:
    assert apply_to_readme(tmp_path, render_block({"reusable-ci"})) == "created"
    content = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert content.startswith(f"# {tmp_path.name}")
    assert START_MARKER in content
