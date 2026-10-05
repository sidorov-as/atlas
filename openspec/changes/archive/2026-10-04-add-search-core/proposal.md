## Why

Atlas has no global search. Users can filter within one entity kind's list page, but cannot type a few words and find an entity, a flow, an API operation or a database table regardless of where it lives. The catalog is assembled from optional plugins, so search must be optional too, must not hard-wire any search engine, and must let each plugin say what is searchable and who may see it.

## What Changes

- A new optional search subsystem. When it is not selected, nothing changes: no routes, no UI, no database objects beyond migrations of installed apps.
- An engine-neutral contract (in the Python plugin API) with three seams that are replaceable independently: **sources** (plugins say what is searchable and how to load and authorize a hit), **engines** (where the index lives and how matches are ranked), and the **HTTP and UI contract** (a stable response shape any UI or client can use).
- A search plugin that owns indexing orchestration, the HTTP API, access control on results, and snippet generation. It depends on no concrete engine.
- A first engine adapter, as a separate plugin, that stores the index in the existing PostgreSQL database and needs no new infrastructure.
- Near-real-time indexing: writes to searchable data mark documents pending in the same transaction, a short-interval job indexes them, and a periodic full rebuild repairs anything missed.
- Search over catalog entities (name, description, documentation) as the first source.
- A global search box and result dialog in the application shell, contributed by a search frontend plugin through a new single-occupant shell contribution; the shell renders nothing when no plugin occupies it.
- Documentation for the index schema, the indexing algorithm, and how to write a source and an engine.

Out of scope here: searching flows, APIs and database schemas (next change), a Meilisearch adapter (later change), searching raw API specification text, deep links into JSON content, typo tolerance as a guaranteed feature, analytics, saved searches, and per-field facets beyond filtering by kind.

## Capabilities

### New Capabilities
- `search-contract`: engine-neutral document, source and engine contracts, registration, and selection of the engine in use.
- `search-indexing`: pending-change tracking, incremental indexing, periodic full rebuild, failure handling and index status.
- `search-api`: the search and status endpoints, result authorization, snippets, filtering and pagination.
- `search-postgres-engine`: an engine adapter that keeps the index in the application's PostgreSQL database.
- `search-catalog-source`: catalog entities as searchable documents.
- `search-ui`: the shell contribution for search and the search box and dialog experience.
- `search-documentation`: documentation of the index schema, the indexing algorithm, and the authoring guides for sources and engines.

### Modified Capabilities

## Impact

- `plugin-api/python`: search contract types and registries. `plugin-api/typescript`: a new single-occupant shell contribution type, composition validation for it.
- `core/frontend`: the shell renders the search contribution when present.
- New plugins: the search plugin (backend and frontend) and the Postgres engine plugin (backend); both appear in the default distribution manifest and lock.
- `core/backend`: catalog registers its source; the search plugin picks its engine at startup from the registered engines (optional `engine` setting) and fails startup when none or an ambiguous choice is found; composition checks that an explicitly named engine plugin is selected and not disabled.
- Container images and the public demo distribution: new plugin sources are copied into the images and the demo's manifest, lock and generated plugin module include search; the demo ships with a prebuilt index.
- Depends on the core scheduler change for the periodic jobs.
- Docs site: new concept, plugin-development and operating pages.
- New database tables owned by the search plugins (pending changes, index status, Postgres index).
