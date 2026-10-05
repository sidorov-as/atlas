---
title: Search engine for PostgreSQL
description: Keep the search index in the application's own PostgreSQL database using full-text search, with no new infrastructure.
audience:
  - operator
  - plugin-author
page-type: feature
plugin-id: atlas.search-postgres
---

# Search engine for PostgreSQL

`atlas.search-postgres` is the engine adapter that stores the [search](search.md)
index in the same PostgreSQL database as the rest of Atlas, so enabling search adds
no service. It only registers an engine; with no search plugin selected nothing uses
it.

## Purpose

It indexes documents into one table with a stored full-text vector and a GIN index.
Title matches outrank body matches. Queries use PostgreSQL `plain` parsing, so every
term is required and query-syntax characters are treated as plain text.

## Dependencies

PostgreSQL and `atlas.search`. The adapter itself does not import the search plugin.

## Enablement and configuration

Select it in the manifest next to `atlas.search`; with only one engine selected it is
used automatically. Choosing between several engines and the `engine` setting are in
[Enable and operate search](../operating-atlas/search.md#choose-the-engine).

| Key | Default | Meaning |
| --- | --- | --- |
| `textSearchConfig` | `simple` | PostgreSQL text-search configuration, for example `english` or `russian` |

`simple` does no stemming or stop-word removal and works for any language, at the
cost of matching exact word forms. Other configurations stem for one language only.
Vectors are built at index time, so after changing the setting run `python manage.py
reindex`. A name that is not a configuration known to the database makes indexing and
queries fail.

## Permissions

Not applicable: the adapter holds no per-user data and authorization is done by
sources. It adds no permissions.

## API surface

Not applicable: no routes. Its tables are described in the [Search index
schema](../reference/search-index.md#postgresql-index-searchindexentry).

## Operations

`replace_all` deletes and refills the table in one transaction, so readers see the old
index until commit and a failure rolls back. It uses `DELETE` rather than `TRUNCATE`
to avoid blocking concurrent queries. Health reports the stored document count, which
lets the search plugin rebuild an empty index at scheduler start. Capacity grows with
the text indexed (bodies are bounded to 100 000 characters by default).

## Extension surface

It is the reference for [Write a search engine](../plugin-development/search-engine.md)
and runs the engine conformance suite in its own tests. It reports `highlights=False`,
so snippets are built by core.

## Limitations

- No typo tolerance; stemming only through a language-specific `textSearchConfig`.
  For typo tolerance see [Run search on
  Meilisearch](../operating-atlas/search-meilisearch.md).
- Ranking is PostgreSQL `ts_rank`; relevance can differ from other engines.
- The index shares the database with Atlas data, so very large indexes compete with
  it for resources.

## Compatibility

Version 0.1.0, atlas core `>=0.1 <1`.

## Troubleshooting

A failing engine shows as `engineHealthy: false` in the status endpoint, and search
answers 503. Check database connectivity and the `engineDetail` administrators see.
After a language change, run `reindex`. See [Enable and operate
search](../operating-atlas/search.md#troubleshooting).
