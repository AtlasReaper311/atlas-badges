"""Concept registry: what atlas-badges can detect and how.

Every concept here is grounded in a greppable signal. If a concept cannot
be detected by a pattern that would convince a human reviewer looking at
the evidence line, it does not belong in this file; it belongs in a repo's
.atlas-concepts.yml include list, written by a human who knows the code.

Colour mapping (brand palette only, so a badged README reads like the site):

  security + infra  -> amber  f5a623  the estate's signature concern gets
                                      the estate's signature colour
  reliability       -> green  4ade80  borrows the status-good semantics:
                                      these are the "stays up" concepts
  data / retrieval  -> paper  e8e8e0  the reading colour, for concepts
                                      about finding and reading things
  ci / plumbing     -> grey   aaa9a0  pipework should recede, not shout
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Signal:
    """One greppable pattern that counts as evidence for a concept.

    pattern     regex applied line by line
    globs       restrict to files whose repo-relative posix path matches
                any of these fnmatch globs; None means every text file
    ignorecase  most signals are prose-adjacent and case-insensitive;
                identifier-shaped signals (env.FOO, DurableObject) are not
    filename    when True, `pattern` is an fnmatch glob tested against the
                repo-relative path itself; the file existing is the evidence
    """

    pattern: str
    globs: tuple[str, ...] | None = None
    ignorecase: bool = True
    filename: bool = False


@dataclass(frozen=True)
class Concept:
    id: str
    name: str
    category: str
    description: str
    signals: tuple[Signal, ...] = field(default_factory=tuple)


# Category display order is deliberate: security and infra first because
# they are the estate's identity, plumbing last.
CATEGORIES: dict[str, dict[str, str]] = {
    "security": {"label": "security", "color": "f5a623"},
    "infra": {"label": "infra", "color": "f5a623"},
    "reliability": {"label": "reliability", "color": "4ade80"},
    "data": {"label": "data", "color": "e8e8e0"},
    "ci": {"label": "ci", "color": "aaa9a0"},
}

WORKFLOW_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml")
WRANGLER_GLOBS = ("wrangler.toml", "wrangler.json", "wrangler.jsonc")

CONCEPTS: tuple[Concept, ...] = (
    Concept(
        id="hmac-verification",
        name="HMAC verification",
        category="security",
        description="Signed-payload verification (webhooks, request signing)",
        signals=(
            Signal(r"crypto\.subtle", ignorecase=False),
            Signal(r"\bHMAC\b", ignorecase=False),
            Signal(r"\bimport\s+hmac\b|\bhmac\.new\b", ignorecase=False),
            Signal(r"X-Hub-Signature"),
            Signal(r"timingSafeEqual|compare_digest", ignorecase=False),
        ),
    ),
    Concept(
        id="scoped-tokens",
        name="Scoped tokens",
        category="security",
        description="Least-privilege credentials, one narrow token per job",
        signals=(
            Signal(
                r"\b[A-Z][A-Z0-9]*_(?:DEPLOY|READ|WRITE|PUBLISH|POST|NOTIFY|PURGE)_(?:TOKEN|KEY)\b",
                ignorecase=False,
            ),
            Signal(r"least[\s-]privilege"),
            Signal(r"read[\s-]only\s+(?:discovery\s+)?token"),
        ),
    ),
    Concept(
        id="cors-allowlist",
        name="CORS allowlisting",
        category="security",
        description="Explicit origin allowlists instead of a wildcard",
        signals=(
            Signal(r"\bALLOWED_ORIGINS?\b", ignorecase=False),
            Signal(r"\ballowedOrigins\b", ignorecase=False),
            Signal(r"origins?[\s_-]*(?:allow|white)list|(?:allow|white)list(?:ed)?[\s_-]*origins?"),
        ),
    ),
    Concept(
        id="durable-objects",
        name="Durable Objects",
        category="infra",
        description="Stateful coordination on the Workers platform",
        signals=(
            Signal(r"\bDurableObject\b", ignorecase=False),
            Signal(r"\benv\.RECORDER\b", ignorecase=False),
            Signal(r"durable_objects", globs=WRANGLER_GLOBS, ignorecase=False),
        ),
    ),
    Concept(
        id="service-bindings",
        name="Service bindings",
        category="infra",
        description="Worker-to-Worker calls without a public network hop",
        signals=(
            Signal(r"\benv\.[A-Z][A-Z0-9_]*\.fetch\s*\(", ignorecase=False),
            Signal(r"\[\[services\]\]", globs=WRANGLER_GLOBS, ignorecase=False),
            Signal(r"\bservices\s*=\s*\[", globs=WRANGLER_GLOBS, ignorecase=False),
            Signal(r"\"services\"\s*:", globs=WRANGLER_GLOBS, ignorecase=False),
        ),
    ),
    Concept(
        id="kv-caching",
        name="KV caching with TTL",
        category="infra",
        description="Edge caching with explicit expiry and observable hits",
        signals=(
            Signal(r"\benv\.[A-Za-z0-9_]*KV\b|\benv\.[A-Z0-9_]*CACHE\b", ignorecase=False),
            Signal(r"\bexpirationTtl\b", ignorecase=False),
            Signal(r"\bcacheControl\b", ignorecase=False),
            Signal(r"x-[a-z0-9-]*cache", ignorecase=False),
            Signal(r"kv_namespaces", globs=WRANGLER_GLOBS, ignorecase=False),
        ),
    ),
    Concept(
        id="idempotent-ops",
        name="Idempotent operations",
        category="reliability",
        description="Safe to re-run: dedup keys, content-hash identity",
        signals=(
            Signal(r"\bidempoten\w*\b"),
            Signal(r"content[\s_-]?hash"),
            Signal(r"\bdedup\w*\b"),
        ),
    ),
    Concept(
        id="defensive-degradation",
        name="Graceful degradation",
        category="reliability",
        description="Unexpected input degrades to an honest fallback, not a crash",
        signals=(
            Signal(r"\bfallback\b"),
            Signal(r"\bgraceful(?:ly)?\b"),
            Signal(r"\bdegrad(?:e|es|ed|ing|ation)\b"),
            Signal(r"couldn'?t confirm"),
        ),
    ),
    Concept(
        id="rag-vector-search",
        name="RAG / vector search",
        category="data",
        description="Retrieval pipelines: embeddings, vector stores, search endpoints",
        signals=(
            Signal(r"\bchromadb\b"),
            Signal(r"nomic-embed"),
            Signal(r"\bembeddings?\b"),
            Signal(r"vector\s*(?:search|store|db|index)"),
            Signal(r"[\"'`]/search\b"),
        ),
    ),
    Concept(
        id="reusable-ci",
        name="Reusable CI/CD workflows",
        category="ci",
        description="workflow_call reusables with thin per-repo callers",
        signals=(
            Signal(r"workflow_call", globs=WORKFLOW_GLOBS, ignorecase=False),
            Signal(
                r"uses:\s*[\w.-]+/[\w.-]+/\.github/workflows/[\w.-]+@",
                globs=WORKFLOW_GLOBS,
                ignorecase=False,
            ),
        ),
    ),
    Concept(
        id="containerised-builds",
        name="Containerised builds",
        category="ci",
        description="Docker-backed local services with compose as the CI gate",
        signals=(
            Signal("Dockerfile", filename=True),
            Signal("docker-compose.yml", filename=True),
            Signal("docker-compose.yaml", filename=True),
            Signal("compose.yml", filename=True),
            Signal("compose.yaml", filename=True),
            Signal(r"docker\s+compose\s+build", globs=WORKFLOW_GLOBS),
        ),
    ),
)

CONCEPTS_BY_ID: dict[str, Concept] = {c.id: c for c in CONCEPTS}
CATEGORY_ORDER: tuple[str, ...] = tuple(CATEGORIES.keys())


def sort_key(concept: Concept) -> tuple[int, str]:
    """Deterministic ordering: category first, then name. Determinism is
    what makes `apply` idempotent; a set-ordered badge row would produce
    a spurious diff on every run."""
    return (CATEGORY_ORDER.index(concept.category), concept.name.lower())
