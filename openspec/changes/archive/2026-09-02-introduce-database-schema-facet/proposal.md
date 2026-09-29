## Why

Nothing in the current PoC or the program so far exercises a `Facet` — a persisted, plugin-owned, structured aspect of an entity, distinct from a computed view (ADR 0018). This was one of the concrete "maybe" extensions raised in `docs/conversation.txt` (SQL schema for Resources, rendered as a diagram "or however the plugin decides"), and `plugin-architecture.md`'s "Proving the architecture" list names Database Schema specifically because it's the only proof point for the Facet/view split — C4 (change 7) computes its diagrams from existing relation data, not from a facet it owns. Landing this now, with two real plugins (Standard Catalog, APIs) and one capability-targeting plugin (C4) already proven, is the right point to prove the remaining core concept before the harder cross-cutting changes (ingestion, auth, distribution).

## What Changes

- Create `plugins/database-schema/` (backend `atlas_plugin_database_schema` + frontend `@atlas/plugin-database-schema`), declaring a manifest dependency on `atlas.standard-catalog` (attaches to `Resource`).
- Add a `DatabaseSchema` Facet: a `OneToOne` model on `CatalogEntity` (not on `ResourceDetails` — Facets attach to the core identity, per `plugin-architecture.md:167`) storing `dialect`, `source_sql`, `parsed_schema` (structured, parsed from `source_sql`), and `parse_status`.
- Declare a new entity capability `schema.host.v1`, provided by `resource` (specifically resources of type `database`, or all resources — decide in design.md).
- Add a facet editor UI (SQL input) on the entity detail page and a computed **ER Diagram** view/tab, gated by `entitySupports('schema.host.v1')`, rendered from the parsed schema — proving one facet can back a computed view the same way `plugin-architecture.md`'s example describes.
- Add facet CRUD as a plugin-owned endpoint (`/api/plugins/atlas.database-schema/...`), not through the generic Entity Service (Facets are explicitly *not* part of the kind's core `spec`/lifecycle, per ADR 0018 — they have their own lifecycle).

## Capabilities

### New Capabilities
- `entity-facets`: a plugin can attach a persisted, typed, structured aspect to any `CatalogEntity` via its own `OneToOne` model and API, without adding fields to core or the owning kind's own tables; a Facet's data and lifecycle are independent of any view that renders it, and removing a view contribution does not delete Facet data.
- `database-schema-plugin`: a Resource may carry a `DatabaseSchema` Facet (dialect, source SQL, parsed schema); when present, an ER Diagram view renders it.

## Impact

- **Backend**: new `plugins/database-schema/backend/`; `DatabaseSchema` model + migration; SQL parsing logic (dialect-aware, scope to be bounded in design.md — this is genuinely new functionality, not a PoC behavior being preserved).
- **Frontend**: new `plugins/database-schema/frontend/`; a facet editor on Resource's detail page; a new ER Diagram tab gated by `schema.host.v1`.
- **First facet, first plugin-owned non-lifecycle endpoint namespace, second capability declaration (after `architecture.subject.v1`)** — validates that the capability-string shape from change 7 generalizes to an unrelated concern.
- **No existing spec is modified** — this is entirely new functionality; no PoC behavior currently covers SQL schemas or ER diagrams.
