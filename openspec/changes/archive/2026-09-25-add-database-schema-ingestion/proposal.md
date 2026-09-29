## Why

Teams that already maintain their database schema as a `.sql` file in their repository have no way to keep the catalog's `DatabaseSchema` Facet on the corresponding `Resource` in sync with it — today that Facet can only be attached or edited by hand through its own dedicated CRUD endpoint (`DatabaseSchemaController`). `catalog-info.yaml` ingestion has no notion of it at all: `ResourceSpecPatch` carries no schema-related field. This change lets a `Resource` manifest point at a `.sql` file in the repository and have ingestion keep the Facet current automatically, the same way it already keeps a `Resource`'s core fields current.

This is a separate, independent change from the sibling `add-ingestion-manifest-includes` change (which adds `kind: Include` manifest composition and generalized admin-visible ingestion-failure tracking) — the two touch the same plugin but nothing here depends on that change's implementation.

## What Changes

- Add an optional `databaseSchema: { dialect, sourceSqlPath }` field, populated only via ingestion's own manifest-facing schema (not the general-purpose `ResourceSpecPatch` used by the manual CRUD API — see design.md for why). `sourceSqlPath` is a path to a `.sql` file, resolved relative to the directory of the manifest file that declares it.
- Ingestion fetches the referenced `.sql` file's content itself via the existing `SourceConnector.fetch_file`, exactly as it already fetches manifest content.
- Add a new `atlas.ingestion.facet_writers.v1` extension point, owned by `atlas_plugin_ingestion`, alongside its existing `connectors`/`parsers` extension points. A registered facet-writer exposes `apply(entity, dialect, source_sql)` and `clear(entity)`.
- `atlas_plugin_database_schema` gains a `register_runtime()` (it currently has none) that registers its own facet-writer implementation — `apply` reuses the existing `parse_schema()` to write/update the `DatabaseSchema` Facet; `clear` removes/resets it.
- After a `Resource`'s normal EntityService-mediated upsert, ingestion resolves and calls the registered `'database-schema'` facet-writer if a `databaseSchema` block was declared (`apply`), or if one was previously declared and no longer is (`clear`) — full-overwrite semantics, symmetric to how `reconcile_declared_relationships` already creates/updates and prunes YAML-origin Architecture Relationships in a second, non-EntityService pass.
- **BREAKING (behavioral, not API-shape)**: `DatabaseSchemaController`'s manual write endpoints (`POST`/`PATCH`) now reject a write when the owning entity's `source_kind == SOURCE_YAML` — a Resource's Facet becomes off-limits to manual edits once that Resource is YAML-managed, matching how every other kind of YAML-managed entity data already behaves. This has no effect on any Resource that isn't YAML-managed.

## Capabilities

### New Capabilities
- `ingestion-database-schema`: Ingestion of a Resource's `DatabaseSchema` Facet from a manifest-declared `sourceSqlPath`, via the new `atlas.ingestion.facet_writers.v1` extension point.

### Modified Capabilities
- `database-schema-plugin`: `DatabaseSchemaController`'s manual write path gains a new precondition (reject when the owning entity is YAML-managed).

## Impact

- **Code**: `plugins/ingestion/backend/atlas_plugin_ingestion/extension_points.py` (new `facet_writers` extension point), `pipeline.py`/`upsert.py` (call `apply`/`clear` after Resource upsert), a new ingestion-manifest-only schema carrying `databaseSchema` (not `ResourceSpecPatch` itself); `plugins/database-schema/backend/atlas_plugin_database_schema/plugin.py` (new `register_runtime()`), `api/views.py` (`source_kind` check in `_check_write_permission`), `parser.py` (reused as-is, unchanged).
- **Specs**: new `specs/ingestion-database-schema/spec.md`; a delta spec for `database-schema-plugin`. No change needed to `entity-facets` or `ingestion-plugin`'s existing requirement text — this change doesn't route the Facet write through `EntityService`/the kind handler (so `entity-facets`'s "Facet write does not invoke the entity's kind handler" and `ingestion-plugin`'s "all entity changes flow through the core Entity Service" both continue to hold as written), it only adds a scoped, explicit exception to manual-write access for this one Facet, documented in design.md rather than as a change to either spec's normative text.
- **Data**: no new migration on `atlas_plugin_database_schema`'s existing `DatabaseSchema` model (its shape is unchanged); no migration on `atlas_plugin_ingestion` either (the extension point is in-memory registry state, like `connectors`/`parsers`).
- **Operators**: a Resource with `spec.databaseSchema` in its manifest gets its ER-Diagram-backing Facet kept in sync automatically; anyone who previously edited that Facet by hand on a YAML-managed Resource loses that ability going forward.
