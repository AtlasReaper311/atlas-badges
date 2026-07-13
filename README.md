# atlas-badges

Scans a local repo clone for greppable evidence of specific engineering
concepts and writes a shields.io badge block into its `README.md`. A senior
engineer skimming the estate for ninety seconds sees proof-of-concept labels
(HMAC verification, KV caching with TTL, service bindings), not just
language pills.

The design rule throughout: **never assert without evidence.** `scan` prints
the file and line for every detection so you can judge whether it is honest
before trusting it, and a per-repo override file exists precisely because
static scanning has limits.

## Install

```bash
pip install -e ".[dev]"     # from this directory; editable + pytest/ruff
```

Cross-platform: pure Python 3.10+, PyYAML is the only runtime dependency.
Works identically from PowerShell and WSL.

## Usage

```bash
atlas-badges scan  ~/repos/github-pulse          # evidence report
atlas-badges scan  ~/repos/github-pulse --json   # machine-readable
atlas-badges apply ~/repos/github-pulse --dry-run
atlas-badges apply ~/repos/github-pulse          # writes README.md
```

`apply` injects (or updates in place) a block between these markers:

```
<!-- ATLAS_CONCEPT_BADGES:START -->
<!-- ATLAS_CONCEPT_BADGES:END -->
```

Everything outside the markers is never touched. If no markers exist yet,
the block is inserted directly under the first `# ` heading. Re-running
`apply` on an unchanged repo is byte-identical and reports `unchanged`,
so it can run in CI without generating noise commits.

## Overrides: `.atlas-concepts.yml`

```yaml
# force-include a concept the code demonstrates but no pattern can see
include:
  - rag-vector-search

# force-exclude a false positive
exclude:
  - kv-caching
```

If an id appears in both lists, exclude wins: when the human record
disagrees with itself, the safer read is to claim less. Unknown ids warn
and are skipped; a stale override never breaks a scan.

## Concept vocabulary

| id | badge | signal basis |
|---|---|---|
| `hmac-verification` | security | `crypto.subtle`, `HMAC`, `X-Hub-Signature`, `timingSafeEqual`, `compare_digest` |
| `scoped-tokens` | security | narrow token names (`*_DEPLOY_TOKEN`, `*_READ_TOKEN`), least-privilege prose |
| `cors-allowlist` | security | `ALLOWED_ORIGINS`, `allowedOrigins`, origin allowlist prose |
| `durable-objects` | infra | `DurableObject`, `env.RECORDER`, `durable_objects` in wrangler config |
| `service-bindings` | infra | `env.<BINDING>.fetch(`, `[[services]]` in wrangler config |
| `kv-caching` | infra | `env.*KV`, `expirationTtl`, `cacheControl`, `x-*-cache`, `kv_namespaces` |
| `idempotent-ops` | reliability | `idempoten*`, content-hash keys, `dedup*` |
| `defensive-degradation` | reliability | `fallback`, `graceful`, `degrad*`, "couldn't confirm" |
| `rag-vector-search` | data | `chromadb`, `nomic-embed`, `embedding(s)`, vector store/search, `"/search"` routes |
| `reusable-ci` | ci | `workflow_call` and reusable-workflow `uses:` lines, workflow files only |
| `containerised-builds` | ci | `Dockerfile` / compose file presence, `docker compose build` in workflows |

`containerised-builds` is the one extension beyond the original ten: it is
grounded in file existence plus the estate's actual CI gate, which is about
as greppable as a signal gets.

## Colour mapping

Brand palette only, so a badged README reads like a strip of the site:

- **security + infra, amber `f5a623`**: the estate's signature concern
  gets the estate's signature colour
- **reliability, green `4ade80`**: borrows the status-good semantics;
  these are the "stays up" concepts
- **data, paper `e8e8e0`**: the reading colour, for concepts about
  finding and reading things
- **ci, grey `aaa9a0`**: pipework should recede, not shout

All badges pin `labelColor=0a0a0f` (site background) and `style=flat-square`
(the estate is square corners and hard edges).

## Tests

```bash
pytest
```

Detectors are tested against synthetic snippets, not real repos: one
positive fixture per concept, a quiet control repo, self-reference
protection (a generated badge block never feeds the next scan), and full
splice/idempotency coverage.

## Try it

```bash
atlas-badges scan examples/demo-repo
atlas-badges apply examples/demo-repo --dry-run
```

The demo repo is a synthetic Worker-shaped fixture with an override file,
so you can see the whole workflow without pointing at a real clone.

---

Part of [atlas-systems.uk](https://atlas-systems.uk)
