---
title: Enable and operate search
description: Select the search plugin and an engine, configure intervals, rebuild the index, read status, and run without a scheduler.
audience:
  - operator
page-type: task
---

# Enable and operate search

Use this page to turn on global search in a distribution, confirm the index is
being built, and keep it healthy. Search is optional; the concepts are in [Search
architecture](../concepts/search-architecture.md). The default distribution
already selects `atlas.search` and `atlas.search-postgres`.

## Prerequisites

- A distribution manifest you can edit (see [Assembling a
  distribution](../configuration/distributions.md)). The checked-in default files
  are Atlas's own distribution; copy them for your own.
- A running scheduler for near-real-time freshness (`python manage.py
  runapscheduler`, the `ingestor` service in the Compose files). Without it, see
  [Run without a scheduler](#run-without-a-scheduler).
- PostgreSQL, for the bundled engine. For [Meilisearch](search-meilisearch.md) you
  also need that service or an existing instance.

## Select the plugins

Add the search plugin and one engine plugin to `plugins:`:

```yaml
plugins:
  - id: atlas.search-postgres
    version: 0.1.0
    backend:
      package: atlas-plugin-search-postgres
      source: workspace

  - id: atlas.search
    version: 0.1.0
    backend:
      package: atlas-plugin-search
      source: workspace
    frontend:
      package: "@atlas/plugin-search"
      source: workspace
```

Resolve and validate the lock, then rebuild and migrate:

```shell
uv run --project composer atlas-compose resolve distributions/default/manifest.yaml -o distributions/default/lock.yaml
uv run --project composer atlas-compose validate distributions/default/manifest.yaml distributions/default/lock.yaml
```

Run migrations from `core/backend` (`uv run python manage.py migrate`). The catalog
source registers itself; no extra step makes catalog entities searchable.

Removing both plugins from the manifest removes the feature: no route, no search box,
no jobs. The tables stay unused and no existing table changed.

## Choose the engine

The search plugin uses exactly one registered engine, chosen at startup:

| Selected engine plugins | `engine` setting | Result |
| --- | --- | --- |
| none | any | Startup fails: an engine plugin is required |
| one | unset | That engine is used |
| one | names it | That engine is used |
| one | names another plugin | Startup fails |
| several | names one | That engine is used |
| several | unset | Startup fails and lists the engines found |

Pin the engine under the search plugin's `config`:

```yaml
  - id: atlas.search
    # ...artifacts as above
    config:
      engine: atlas.search-postgres
```

To use Meilisearch instead of PostgreSQL, follow [Run search on
Meilisearch](search-meilisearch.md); it covers the service, key, volume and rebuild,
and points to a runnable example (`make examples-up EXAMPLE=search-meilisearch`).

Composition checks that a named engine plugin is in the manifest, not disabled and
has a backend artifact, and reports a composition error otherwise (see [Fix
composition errors](composition-errors.md)). The other cases are detected when the
backend starts, before it serves traffic, with a message naming the engines found.

## Configuration

All keys are optional and go under the plugin's `config:` in the manifest.

| Plugin | Key | Default | Meaning |
| --- | --- | --- | --- |
| `atlas.search` | `engine` | unset | Plugin id of the engine to use |
| `atlas.search` | `drainIntervalSeconds` | `10` | How often pending changes are indexed |
| `atlas.search` | `rebuildIntervalSeconds` | `21600` (6 h) | How often the whole index is rebuilt |
| `atlas.search` | `maxBodyChars` | `100000` | Bound on an indexed document body |
| `atlas.search` | `minQueryLength` | `2` | Shorter queries return nothing |
| `atlas.search-postgres` | `textSearchConfig` | `simple` | PostgreSQL text-search configuration, for example `english` or `russian` |

`simple` applies no stemming or stop words and behaves the same for every language.
Vectors are built when a document is indexed, so after changing `textSearchConfig`
run `reindex`. Interval changes take effect when the scheduler restarts.

## Build or rebuild the index

At scheduler start, the index is built automatically once if the engine is empty
while the catalog is not. To rebuild at any time, from `core/backend`:

```shell
uv run python manage.py reindex
```

It prints `Indexed N documents` and fails with a message if search is inactive, if
another indexing run holds the lock, or if the engine fails. The previous index
stays queryable while it runs. Use it after enabling search, switching engines or
changing `textSearchConfig`.

## Check status

`GET /api/plugins/atlas.search/status/` with an authenticated session reports
`pendingCount`, `oldestPendingAgeSeconds`, `lastDrainAt`, `lastRebuildAt`, health and
error flags. Administrators additionally see the engine id, document count, last
error and effective intervals. All fields are described in the [Search index
schema](../reference/search-index.md#status-response). A healthy index shows
`ok: true` and a small, short-lived backlog.

The search dialog itself shows a notice when the oldest pending change is older than
two minutes. To find the cause of a stale index, use [Diagnosing a stale
index](../concepts/search-indexing.md#diagnosing-a-stale-index).

## Run without a scheduler

Some deployments, such as the public demo, run a single small container with no
scheduler. Build the index ahead of time instead:

1. Seed the catalog.
2. Run `python manage.py reindex` in the same build step. The demo's
   `deploy/render/build-demo-db.sh` does this right after seeding.
3. Start the application. Search returns results from the first request.

Edits made while no scheduler runs stay in the pending table and are not searchable
until a drain or rebuild runs, for the demo at the next restart. Status reports the
backlog and the search dialog shows the stale-index notice, so it is visible rather
than silent. The pending table is bounded by the number of documents.

## Troubleshooting

| Symptom | Cause and action |
| --- | --- |
| No search box in the UI | `@atlas/plugin-search` is not in the distribution, or search is unavailable; the shell renders nothing when no plugin occupies the slot |
| Search dialog says search is unavailable | The engine failed (HTTP 503). Check engine health in status and the backend log |
| Search endpoint returns 404 | The search plugin is not selected or is disabled |
| Backend exits at startup naming search engines | No engine, an ambiguous choice, or `engine` names a plugin that registered none; fix the selection above |
| Results empty after enabling | Run `reindex`, then confirm `documentCount` in status |
| A new or edited entity is not found | Check the scheduler and the backlog, see [Search indexing algorithm](../concepts/search-indexing.md) |
