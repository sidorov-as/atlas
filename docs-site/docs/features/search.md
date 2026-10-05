---
title: Search
description: Find catalog entities with a global search box and dialog, backed by a swappable index engine and per-plugin authorization.
audience:
  - catalog-user
  - operator
  - plugin-author
page-type: feature
plugin-id: atlas.search
---

# Search

`atlas.search` adds a global search box and a results dialog. A user types a few
words and finds an entity by name, description or documentation wherever it lives.
It owns indexing, the search and status endpoints, result authorization and
snippets. It names no engine and is optional.

## Purpose and use

Open the search box in the application shell, or press `Ctrl+K` (`Cmd+K` on macOS).
Type at least two characters; queries are sent after a short pause. Each result
shows a kind label, the title and a snippet with matches highlighted. Use the arrow
keys and `Enter` to open a result, `Esc` to close. The dialog shows an empty state,
an unavailable state when the engine fails and a notice when the index is behind.

Searchable today: catalog entities of kind System, Component, Resource, API and
Group, plus content from optional plugins when they are selected: flows
(`atlas.flows`), API endpoints and operations (`atlas.apis`) and database schemas
(`atlas.database-schema`). A match inside a flow's steps or a schema's tables opens
the whole flow or the owning resource's schema tab, not the step or table. Raw
OpenAPI and AsyncAPI documents are not searched. Per-kind list pages keep their own
filtering.

## Dependencies

- **Backend:** an engine plugin; `atlas.search-postgres` is bundled. Sources
  register from their own plugins.
- **Scheduler:** the core scheduler runs the drain and rebuild jobs.
- **Frontend:** `@atlas/plugin-search` contributes the box and dialog. The backend
  plugin works without it, and the UI works only with the backend plugin.

## Enablement and configuration

Select `atlas.search` and one engine in the manifest, then run migrations and
`reindex`. Keys (`engine`, `drainIntervalSeconds`, `rebuildIntervalSeconds`,
`maxBodyChars`, `minQueryLength`), engine choice and running without a scheduler are
in [Enable and operate search](../operating-atlas/search.md).

## Permissions

Every request needs an authenticated session. Which results an actor sees is decided
by each source's `resolve`; for catalog entities, flows and database schemas any
authenticated user may read what is active, and API endpoints and operations follow
the APIs plugin's read permissions. The status endpoint shows full operational detail only to holders of
`atlas.search.status.admin` (superusers by default).

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/plugins/atlas.search/search/` | Ranked, authorized results with snippets |
| `GET /api/plugins/atlas.search/status/` | Engine health, backlog and last runs |

Parameters and fields are in the [Search index schema](../reference/search-index.md);
signatures are in the [HTTP API](../api-reference/index.md).

## Operations

Jobs `atlas.search.drain` (10 s), `atlas.search.rebuild` (6 h) and
`atlas.search.initial_rebuild` (once at scheduler start) are registered with the
core scheduler. The management command `reindex` rebuilds on demand. See
[Search indexing algorithm](../concepts/search-indexing.md) for behaviour and
failure handling.

## Extension surface

- [Write a search source](../plugin-development/search-source.md) to make other data
  searchable.
- [Write a search engine](../plugin-development/search-engine.md) to store the index
  elsewhere.
- Contribute your own component to the single-occupant search extension point to
  replace the UI.

See [Search architecture](../concepts/search-architecture.md).

## States

- **Not selected:** no routes, no search box, no jobs, no writes to search tables.
- **Disabled:** the app stays installed but the plugin is inert; both endpoints
  answer 404 and no changes are recorded.
- **Removed from the manifest:** the feature disappears; its tables remain unused
  until purged.

## Limitations

- Totals are approximate: pages are filled by over-fetching, so a page may be
  short and `total` is a lower bound while more results exist.
- Edits are searchable after the next drain (about ten seconds with a scheduler).
  Bulk operations that bypass model signals are repaired by the rebuild.
- Typo tolerance and identical relevance across engines are not guaranteed.
- Edits made while no scheduler runs are not searchable until the next rebuild.

## Compatibility

Plugin version 0.1.0, atlas core `>=0.1 <1`. The contract package is a 0.x
interface and may change before it is stabilized.

## Troubleshooting

Use the table in [Enable and operate search](../operating-atlas/search.md#troubleshooting)
and [Diagnosing a stale index](../concepts/search-indexing.md#diagnosing-a-stale-index).
