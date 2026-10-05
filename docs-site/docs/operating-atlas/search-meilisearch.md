---
title: Run search on Meilisearch
description: Switch the search engine from PostgreSQL to Meilisearch, run the service with a persistent volume and an access key, or point Atlas at an instance you already run.
audience:
  - operator
page-type: task
---

# Run search on Meilisearch

`atlas.search-meilisearch` keeps the [search](../features/search.md) index in a
Meilisearch server instead of PostgreSQL. It adds typo tolerance and native
highlighting, at the cost of one more service to run. Use it when the bundled
PostgreSQL engine matches too strictly or the catalog is large. The default
distribution and the public demo stay on PostgreSQL.

A complete, runnable example is in
[`examples/search-meilisearch/`](https://github.com/sidorov-as/atlas/tree/main/examples/search-meilisearch):
a manifest, lock, generated inputs, a standalone Compose stack and a smoke test. Start
it with `make examples-up EXAMPLE=search-meilisearch` and check it with `make
examples-smoke EXAMPLE=search-meilisearch`.

## Prerequisites

- Search already enabled as described in [Enable and operate
  search](search.md).
- Docker Compose for the generated container, or a Meilisearch instance you run
  yourself.
- A scheduler (`runapscheduler`) so the index is filled and kept current.

## Switch the engine

Exactly one engine plugin may be selected, so replace `atlas.search-postgres`
rather than adding to it:

```yaml
plugins:
  - id: atlas.search-meilisearch
    version: 0.1.0
    backend:
      package: atlas-plugin-search-meilisearch
      source: workspace

  - id: atlas.search
    # ...unchanged
```

Selecting both engines stops the backend at startup with an error naming both. The
search plugin, its sources and the UI need no change.

Resolve the lock and generate the deployment inputs:

```shell
uv run --project composer atlas-compose resolve manifest.yaml -o lock.yaml
uv run --project composer atlas-compose generate backend lock.yaml -o generated/selected_plugins.py
uv run --project composer atlas-compose generate compose lock.yaml -o generated/compose.override.yaml
```

The lock now records the `meilisearch` service with its pinned image, port, health
check and data path. The override file adds the container, a health check, a named
volume and the key, and makes `backend` and `ingestor` wait until the service is
healthy.

## Set the access key

The key is never written to the manifest, the lock or generated files; they carry
only the name of the environment variable, `ATLAS_SERVICE_MEILISEARCH_KEY`. Set it in
the deployment environment before starting. Meilisearch requires at least 16 bytes:

```shell
export ATLAS_SERVICE_MEILISEARCH_KEY="$(openssl rand -hex 24)"
docker compose -f docker-compose.yml -f generated/compose.override.yaml up --build
```

Compose refuses to start with a message naming the variable if it is unset. The same
key is used for indexing and searching. Searches only come from the backend and
authorization stays in Atlas, so the key is not exposed to browsers. To rotate it,
change the variable and recreate the `meilisearch`, `backend` and `ingestor`
containers; the index itself survives, because the key is not part of the data.

## Persistent data

The generated service mounts the named volume `meilisearch-data` at `/meili_data`.
The index survives container recreation and upgrades. If you remove the volume, the
index starts empty and search returns nothing until the next rebuild; run
[`reindex`](#rebuild-after-switching) instead of waiting. The periodic rebuild also
repairs a lost or damaged index. Atlas does not back up the volume; the index can
always be recreated from the catalog.

## Rebuild after switching

A new engine starts empty and nothing migrates the old index. After the first
deployment with the new engine:

1. Wait for the scheduler's first-run rebuild, or run it now from `core/backend`:

   ```shell
   uv run python manage.py reindex
   ```

2. Check `GET /api/plugins/atlas.search/status/`. As an administrator you see the
   engine id `atlas.search-meilisearch`, a healthy engine and a `documentCount` that
   matches the catalog.

Replacement builds a temporary index and swaps it with the live one, so queries
during a rebuild see either the old or the new content. If the build fails, the
previous index stays active and the temporary one is deleted. To go back, select
`atlas.search-postgres` again, regenerate and rebuild; the Meilisearch service and its
volume can then be removed.

## Use an instance you already run

Mark the service as external on the plugin entry and give its address:

```yaml
  - id: atlas.search-meilisearch
    version: 0.1.0
    backend:
      package: atlas-plugin-search-meilisearch
      source: workspace
    services:
      meilisearch:
        external: true
        address: http://meilisearch.internal:7700
```

No container or volume is generated. The plugin connects to that address with the key
from `ATLAS_SERVICE_MEILISEARCH_KEY`, which must match the instance's key.
`external: true` without an `address` fails composition and names the service. The
address is operator configuration for an internal service; Atlas connects to it
directly and to nothing else.

## Configuration

Keys go under the plugin's `config:`. `url` and `key` are filled in by the composer
from the service; set them yourself only to override.

| Key | Default | Meaning |
| --- | --- | --- |
| `url` | wired from the service | Base URL of the instance |
| `key` | wired as `ATLAS_SERVICE_MEILISEARCH_KEY` | Access key, a secret reference |
| `index` | `atlas-search` | Index uid; letters, digits, `_` and `-` |
| `requestTimeoutSeconds` | `10` | Timeout of one HTTP request |
| `taskTimeoutSeconds` | `60` | How long a write waits for the engine to apply it |

A write counts as done only after Meilisearch has applied it. If it fails or does not
finish within `taskTimeoutSeconds`, the change stays pending and is retried on the
next drain, so raise the timeout for very large rebuilds rather than ignoring errors.

## Troubleshooting

| Symptom | Cause and action |
| --- | --- |
| Compose says `ATLAS_SERVICE_MEILISEARCH_KEY` is not set | Export the key before `docker compose up` |
| Search answers 503, status shows the engine unhealthy | The instance is unreachable or rejects the key. Check the container health and that the key matches |
| Search returns nothing after switching | The new engine is empty. Run `reindex` |
| Backend does not start and names two engines | Both engine plugins are selected; remove `atlas.search-postgres` |
| Composition says the service has no address | `external: true` needs an `address` |
| Writes stay pending, `lastError` mentions a timeout | Raise `taskTimeoutSeconds` or check the instance's load and disk |
