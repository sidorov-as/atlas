---
title: Search index schema
description: Exact search document format, document id rules, catalog field mapping, and the pending-change, status and engine tables.
audience:
  - operator
  - plugin-author
page-type: reference
---

# Search index schema

This page is the lookup reference for the data the search plugins store and
exchange. Authoritative sources: `plugin-api/python/atlas_plugin_api/search.py`
(contract), `plugins/search/backend/atlas_plugin_search/models.py` (pending and
status tables), `plugins/search-postgres/backend/atlas_plugin_search_postgres/models.py`
(PostgreSQL index), `core/backend/server/apps/catalog/search_source.py`
(catalog mapping) and the `search_source.py` module of `atlas_plugin_flows`,
`atlas_plugin_apis` and `atlas_plugin_database_schema` (plugin sources). It applies to the 0.x contract shipped with `atlas.search`
0.1.0. For the design, see [Search architecture](../concepts/search-architecture.md).

## Search document

| Field | Type | Rule |
| --- | --- | --- |
| `id` | string | `<kind>:<key>`. The prefix must equal `kind`, and the id alone must let the owning source reload the live object. |
| `kind` | string | Non-empty, normalized (no surrounding whitespace). Unique to one source across all registered sources. |
| `title` | string | Plain text. Matches here outweigh matches in the body. |
| `body` | string | Plain text, default empty. Bounded to 100 000 characters by default (`maxBodyChars`); longer text is cut at a word boundary and a warning is logged. A single word longer than the bound is cut mid-word. |
| `summary` | string or none | Short description; used for the snippet when the body has no match. |
| `route` | string or none | Opaque hint stored untouched by engines. |

`split_document_id` splits at the first colon, so a key may itself contain
colons.

## Document ids

- A source owns one or more kinds, and every kind is owned by exactly one source.
  Registering a second source for a kind, or the same source id twice, fails with
  the owners named.
- Two sources producing the same document id fails a rebuild with
  `DuplicateSearchDocumentError`.
- A pending or candidate id whose kind no source owns is ignored: pending rows
  are dropped, candidates are skipped.

## Catalog source (`atlas.catalog`)

One document per **active** catalog entity. Removed or purged entities are not
documents. `user` entities have no detail page and are not indexed.

| Document field | Catalog value |
| --- | --- |
| `id` | `<entity kind>:<entity uuid>`, for example `component:3f2c…` |
| `kind` | `system`, `component`, `resource`, `api` or `group` |
| `title` | Entity `name` |
| `body` | `description` and `documentation` joined by a blank line (empty parts omitted) |
| `summary` | Entity `description`, if any |

`resolve` links to `/systems/<id>`, `/components/<id>`, `/resources/<id>`,
`/apis/<id>` or `/teams/<id>`, and labels results *System*, *Component*,
*Resource*, *API* and *Group*. Any authenticated user may read any entity
today, so `resolve` returns nothing only for unauthenticated actors and for ids
that no longer resolve to an active entity.

## Flow source (`atlas.flows`)

Registered by the flows plugin. One document per flow whose owning system is
active.

| Document field | Flow value |
| --- | --- |
| `id` | `flow:<flow id>` (the integer primary key) |
| `kind` | `flow` |
| `title` | Flow `name` |
| `body` | `description`, `documentation` and the [flattened step text](#flattening-rules), joined by a blank line (empty parts omitted) |
| `summary` | Flow `description`, if any |

Watched models: `Flow` and the catalog entity. A flow change maps to its own id; a
change to a `system` entity maps to the ids of all flows of that system, so renaming
or removing the system refreshes or drops them. `resolve` links to `/flows/<id>`,
labels results *Flow* and shows the live title `<flow name> — <system name>`. Any
authenticated user may read any flow, as in the flows API, and a flow of a removed
system is omitted.

## API source (`atlas.apis`)

Registered by the APIs plugin, one source with two kinds. Only rows with status
`active` are documents; a removed row drops out and a restored one returns, both as
plain saves. API entities themselves are catalog documents; stored specification
text and long descriptions are never indexed.

| Document field | Endpoint | Operation |
| --- | --- | --- |
| `id` | `endpoint:<uuid>` | `operation:<uuid>` |
| `kind` | `endpoint` | `operation` |
| `title` | `<METHOD> <path>` | `<direction> <channel address>` |
| `body` | path words, `summary`, `operation_id` | channel address words, `summary`, `operation_id` |
| `summary` | `summary`, if any | `summary`, if any |

Watched models: `ApiEndpoint` and `ApiOperation`. `resolve` checks
`atlas.apis.endpoint.read` and `atlas.apis.operation.read` for the actor, loads live
rows, omits rows that are removed or whose API is no longer active, and links to
`/apis/<api id>/endpoints/<id>` or `/apis/<api id>/operations/<id>`. Results are
labelled *Endpoint* and *Operation*, and the live title is
`<document title> — <API title or name>`, so renaming an API needs no reindex.

Soft removal of endpoints and operations (spec re-import, the admin action) saves
each row so the change reaches the index. A bulk `QuerySet.update` sends no change
signal; the periodic rebuild would be the only repair.

## Database schema source (`atlas.database-schema`)

Registered by the database schema plugin. One document per schema facet whose owner
is an active entity of a kind that hosts schemas (`schema.host.v1`).

| Document field | Schema value |
| --- | --- |
| `id` | `schema:<owning entity uuid>` |
| `kind` | `schema` |
| `title` | Owning entity `name` |
| `body` | Table and column names from the parsed structure, see [flattening rules](#flattening-rules); empty when the parse failed |

Watched models: the facet and the catalog entity. Because the title is the owner's
name, a change to an entity maps to its schema document when it has one. `resolve`
links to `/resources/<id>?tab=schema`, labels results *Database schema* and takes
the title from the live entity. Any authenticated user may read a schema of an
active owner. A facet with `parse_status` `failed` stays searchable by the owner's
name only, and one unreadable parsed structure never stops other documents from
being indexed. Raw `source_sql` is never indexed.

## Flattening rules

JSON content is turned into plain text by one small function per source, so a change
of the JSON shape breaks one function and its test rather than search. Anything
unexpected is skipped without an error.

| Source | Function | Text taken |
| --- | --- | --- |
| Flows | `flatten_step_text` | Each step's `title`, `summary` and `external_label`, trimmed, one per line. Steps backed by a reference (entity, endpoint, event, flow) carry no authored text and add nothing. Non-list `steps`, non-object steps and blank or non-string values are ignored. |
| Database schema | `flatten_schema_text` | `tables[].name` and `tables[].columns[].name` of the parsed structure, one table per line. Each name is written as is and, when it contains separators, again split into words (`order_items` also gives `order items`). Anything else in the structure is ignored. |
| APIs | body builder | The path or channel address split into words (`/pets/{petId}` gives `pets petId`), then `summary` and `operation_id`. |

PostgreSQL's text parser keeps paths and dotted names as one token, so `/pets` or
`orders.created` would not match a search for `pets` or `created`. The word-split copy
in the body is what makes partial matches work; titles are shown unchanged. Large
flows and schemas are bounded by `maxBodyChars`.

## Whole-entity links

A match inside step text, a table or a column opens the whole flow or schema view.
The index has no anchors for steps, tables or columns, and links are
application-relative paths from `resolve`. The schema link selects the owner's
*Schema* tab with the `tab` query parameter.

## Pending changes (`PendingChange`)

| Column | Meaning |
| --- | --- |
| `document_id` | Unique, up to 512 characters. One row per document. |
| `generation` | Starts at 1; incremented each time the same document changes while still pending. |
| `queued_at` | When the row was first queued. Drives the oldest-pending age in status. |

A row is deleted only while its `generation` still equals the one the indexer
read, so a change that lands mid-run stays pending.

## Index status (`IndexStatus`)

A singleton row (`pk=1`).

| Column | Meaning |
| --- | --- |
| `last_drain_at`, `last_rebuild_at` | Last successful run of each job. |
| `last_error`, `last_error_at` | Most recent failure message (cut to 2000 characters) and time. |
| `last_error_job` | `drain` or `rebuild`. Only a success of the same job clears the error. |

## PostgreSQL index (`SearchIndexEntry`)

Owned by `atlas.search-postgres`.

| Column | Meaning |
| --- | --- |
| `document_id` | Unique id. |
| `kind` | Document kind, used for the kind filter. |
| `title`, `body` | Stored copies of the indexed text. |
| `search_vector` | Stored `tsvector`: title lexemes weight `A`, body lexemes weight `B`. A GIN index (`search_pg_vector_gin`) covers it. |

Queries use PostgreSQL `plain` parsing: every term is ANDed and tsquery syntax
characters are treated as data. Results order by rank descending, then
`document_id`.

## Status response

`GET /api/plugins/atlas.search/status/` needs an authenticated session.

| Field | Visible to | Meaning |
| --- | --- | --- |
| `ok` | everyone | Engine healthy and no recorded error. |
| `engineHealthy`, `hasError` | everyone | The two parts of `ok`. |
| `pendingCount`, `oldestPendingAgeSeconds` | everyone | Backlog size and age of the oldest row (`null` when empty). |
| `lastDrainAt`, `lastRebuildAt` | everyone | Last successful runs. |
| `engine`, `engineDetail`, `documentCount` | administrators | Engine id, health detail, indexed documents. |
| `lastError`, `lastErrorAt`, `lastErrorJob` | administrators | Last failure. |
| `drainIntervalSeconds`, `rebuildIntervalSeconds` | administrators | Effective intervals. |

Administrators are actors who hold the `atlas.search.status.admin` permission
(granted to superusers by the built-in evaluator). Other actors receive only the
common fields.

## Search response

`GET /api/plugins/atlas.search/search/?q=&kinds=&page=&pageSize=`

| Parameter | Rule |
| --- | --- |
| `q` | Text query. Shorter than `minQueryLength` (default 2) returns an empty page without querying the engine. |
| `kinds` | Optional comma-separated kinds. Unknown kinds are ignored; if none are known the page is empty. |
| `page` | 1-based, default 1. |
| `pageSize` | 1 to 50, default 20. |

Each result has `id`, `kind`, `kindLabel`, `title`, `link` and `snippet`
(`text` plus `matches`, a list of `[start, end)` offsets into `text` in UTF-16 code
units, so a character outside the Basic Multilingual Plane such as an emoji counts as
two; slice the text with them as JavaScript does). The snippet is plain text, never
markup. The envelope adds `total`, `page`,
`pageSize` and `hasMore`. The endpoint answers 404 when the plugin is inactive
and 503 when the engine fails. Generated OpenAPI is authoritative for exact
signatures; see the [HTTP API](../api-reference/index.md).
