"""Detector tests against small synthetic snippets.

Each concept gets a positive fixture proving its signal fires with real
evidence, and one shared control repo proves quiet code stays quiet.
Fixtures are synthetic on purpose: the detectors are tested against the
patterns they claim to match, not against any one real repo's quirks.
"""

from __future__ import annotations

from pathlib import Path

from atlas_badges.scanner import scan_repo

# concept id -> {relative path: file content}
POSITIVE_FIXTURES: dict[str, dict[str, str]] = {
    "hmac-verification": {
        "src/index.js": (
            'const key = await crypto.subtle.importKey("raw", secret, '
            '{ name: "HMAC", hash: "SHA-256" }, false, ["sign"]);\n'
            'const given = request.headers.get("X-Hub-Signature-256");\n'
        ),
    },
    "scoped-tokens": {
        "src/deploy.js": (
            "// deploy path uses CF_WORKERS_DEPLOY_TOKEN, runtime uses a\n"
            "// separate PAGES_READ_TOKEN; least-privilege throughout\n"
        ),
    },
    "cors-allowlist": {
        "src/cors.js": (
            "const ALLOWED_ORIGINS = ['https://atlas-systems.uk'];\n"
            "if (ALLOWED_ORIGINS.includes(origin)) "
            "headers['Access-Control-Allow-Origin'] = origin;\n"
        ),
    },
    "durable-objects": {
        "src/recorder.js": (
            "export class Recorder extends DurableObject {\n"
            "  async fetch(request) { return this.env.RECORDER.fetch(request); }\n"
            "}\n"
        ),
        "wrangler.toml": '[[durable_objects.bindings]]\nname = "RECORDER"\n',
    },
    "service-bindings": {
        "src/index.js": 'const res = await env.GITHUB_PULSE.fetch("https://pulse/pulse");\n',
        "wrangler.toml": '[[services]]\nbinding = "GITHUB_PULSE"\nservice = "github-pulse"\n',
    },
    "kv-caching": {
        "src/index.js": (
            'await env.PULSE_KV.put(key, body, { expirationTtl: 3600 });\n'
            'headers["x-pulse-cache"] = "HIT";\n'
        ),
        "wrangler.toml": '[[kv_namespaces]]\nbinding = "PULSE_KV"\n',
    },
    "idempotent-ops": {
        "src/dedupe.py": (
            "# posting is idempotent: the dedup key is a content-hash of the\n"
            "# outcome, so the same result never notifies twice\n"
        ),
    },
    "defensive-degradation": {
        "src/render.js": (
            "// unexpected shape degrades to the fallback formatter with an\n"
            '// honest "couldn\'t confirm this" line, never a crash\n'
        ),
    },
    "rag-vector-search": {
        "src/search.py": (
            "import chromadb\n"
            'EMBED_MODEL = "nomic-embed-text"\n'
            '@app.get("/search")\n'
            "def search(q: str): ...\n"
        ),
    },
    "reusable-ci": {
        ".github/workflows/deploy.yml": (
            "on:\n  push:\njobs:\n  deploy:\n"
            "    uses: AtlasReaper311/atlas-infra/.github/workflows/deploy-worker.yml@main\n"
        ),
    },
    "containerised-builds": {
        "Dockerfile": "FROM python:3.12-slim\n",
        ".github/workflows/ci.yml": "run: docker compose build\n",
    },
}

# Deliberately quiet code: plain logic, no signal words, no signal files.
CONTROL_FIXTURE = {
    "src/maths.py": (
        "def area(width, height):\n"
        "    return width * height\n\n"
        "def total(values):\n"
        "    return sum(values)\n"
    ),
    "README.md": "# control\n\nA small library that adds numbers together.\n",
}


def _write_fixture(root: Path, files: dict[str, str]) -> None:
    for relpath, content in files.items():
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def test_each_concept_fires_with_evidence(tmp_path: Path) -> None:
    for concept_id, files in POSITIVE_FIXTURES.items():
        repo = tmp_path / concept_id
        repo.mkdir()
        _write_fixture(repo, files)

        detections = {d.concept.id: d for d in scan_repo(repo)}
        assert concept_id in detections, f"{concept_id} did not fire on its own fixture"

        detection = detections[concept_id]
        assert detection.total_matches >= 1
        assert detection.evidence, f"{concept_id} fired without evidence"
        for evidence in detection.evidence:
            assert evidence.path in files, "evidence points outside the fixture"


def test_control_repo_stays_quiet(tmp_path: Path) -> None:
    repo = tmp_path / "control"
    repo.mkdir()
    _write_fixture(repo, CONTROL_FIXTURE)
    assert scan_repo(repo) == []


def test_generated_badge_block_is_not_evidence(tmp_path: Path) -> None:
    # A previously applied badge block mentions concept names and markers;
    # it must never feed detections on the next scan.
    repo = tmp_path / "selfref"
    repo.mkdir()
    _write_fixture(
        repo,
        {
            "README.md": (
                "# repo\n\n<!-- ATLAS_CONCEPT_BADGES:START -->\n"
                "![infra: KV caching with TTL](https://img.shields.io/badge/x) "
                "<!-- ATLAS_CONCEPT_BADGES:END -->\n"
            )
        },
    )
    assert scan_repo(repo) == []


def test_override_file_is_never_evidence(tmp_path: Path) -> None:
    # Naming a concept inside .atlas-concepts.yml is a human instruction,
    # not code evidence; only the include/exclude semantics may act on it.
    repo = tmp_path / "cfg"
    repo.mkdir()
    _write_fixture(
        repo,
        {".atlas-concepts.yml": "# idempotent dedup content-hash notes\nexclude: []\n"},
    )
    assert scan_repo(repo) == []


def test_one_line_is_one_piece_of_evidence(tmp_path: Path) -> None:
    # Two patterns of the same concept hitting one line must not produce
    # duplicate evidence rows.
    repo = tmp_path / "dupes"
    repo.mkdir()
    _write_fixture(
        repo,
        {"src/x.js": 'await env.PULSE_KV.put(k, v, { expirationTtl: 3600 });\n'},
    )
    detections = {d.concept.id: d for d in scan_repo(repo)}
    kv = detections["kv-caching"]
    assert kv.total_matches == 1
    assert len(kv.evidence) == 1


def test_skip_dirs_are_ignored(tmp_path: Path) -> None:
    repo = tmp_path / "vendored"
    repo.mkdir()
    _write_fixture(
        repo,
        {
            "node_modules/lib/index.js": "crypto.subtle.sign('HMAC', key, data)\n",
            ".git/hooks/sample": "idempotent\n",
        },
    )
    assert scan_repo(repo) == []


def test_workflow_scoped_signal_ignores_other_files(tmp_path: Path) -> None:
    # `workflow_call` in prose outside .github/workflows/ is documentation,
    # not a reusable workflow.
    repo = tmp_path / "prose"
    repo.mkdir()
    _write_fixture(repo, {"NOTES.md": "someday: look into workflow_call reusables\n"})
    assert scan_repo(repo) == []
