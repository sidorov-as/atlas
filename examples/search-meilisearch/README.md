# Search with Meilisearch

The default distribution keeps the search index in PostgreSQL. This example is
the same distribution with the engine swapped for the Meilisearch adapter
(`atlas.search-meilisearch`) — nothing else in the manifest changes, and the
search plugin, its sources and the UI are untouched.

Exactly one engine plugin may be selected, so the manifest names
`atlas.search-meilisearch` *instead of* `atlas.search-postgres`. Selecting both
stops the search plugin at startup with an error naming both engines.

## What the composer generates

The adapter declares the Meilisearch container it needs. Resolving the manifest
records it in `lock.yaml` (pinned image, port, health check, data path), and:

| Command | Output |
| --- | --- |
| `atlas-compose generate backend lock.yaml -o …` | `generated/selected_plugins.py` — plugin list plus `PLUGIN_CONFIGS` wiring `url` to `http://meilisearch:7700` and `key` to `{fromEnv: ATLAS_SERVICE_MEILISEARCH_KEY}` |
| `atlas-compose generate compose lock.yaml -o …` | `generated/compose.override.yaml` — the `meilisearch` service with a health check and the `meilisearch-data` volume, plus the key and `depends_on` for `initializer`, `backend` and `ingestor` |

The access key is never written to the lock or to generated files, only the
*name* of the environment variable that carries it.

## Run it

From the repository root:

```bash
make examples-up EXAMPLE=search-meilisearch
make examples-smoke EXAMPLE=search-meilisearch   # optional
```

or from this directory:

```bash
cp .env.example .env
docker compose up --build -d
./smoke.sh
```

`.env.example` sets `COMPOSE_FILE=compose.yaml:generated/compose.override.yaml`, so
plain `docker compose` merges the base stack ([`compose.yaml`](compose.yaml): Atlas,
PostgreSQL and the scheduler) with the generated Meilisearch service. It also holds
disposable values, including `ATLAS_SERVICE_MEILISEARCH_KEY` (at least 16 bytes).
Replace them if the stack is reachable by anyone else.

Open <http://localhost:18100> and sign in with `ATLAS_BOOTSTRAP_USERNAME` and
`ATLAS_BOOTSTRAP_PASSWORD` from `.env`. The scheduler builds the empty index on its
first start; to build it immediately run `docker compose exec backend python manage.py
reindex`. The smoke test creates a system, builds the index, and checks that a search
and a search with a typo both find it, and that the status endpoint reports the
`meilisearch` engine.

Stop it and remove its volumes with `make examples-down EXAMPLE=search-meilisearch`.
To go back to PostgreSQL, select `atlas.search-postgres` again and regenerate.

To run it on top of the repository's own `docker-compose.yml` instead:

```bash
export ATLAS_SERVICE_MEILISEARCH_KEY="$(openssl rand -hex 24)"
docker compose -f docker-compose.yml \
  -f examples/search-meilisearch/generated/compose.override.yaml up --build
```

## Use an instance you already run

Uncomment the `services` block on the plugin entry in `manifest.yaml`:

```yaml
services:
  meilisearch:
    external: true
    address: http://meilisearch.internal:7700
```

No container is generated; the plugin connects to that address with the key
from `ATLAS_SERVICE_MEILISEARCH_KEY`.

## Regenerate

```bash
make lock DIST=examples/search-meilisearch
make lock-validate DIST=examples/search-meilisearch
uv run --project composer --with-editable plugins/search-meilisearch/backend \
  atlas-compose generate compose examples/search-meilisearch/lock.yaml \
  -o examples/search-meilisearch/generated/compose.override.yaml
```
