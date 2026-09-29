## Context

`DatabaseSchema` is a Facet (`entity-facets` spec): a `OneToOneField(CatalogEntity, primary_key=True)` model owned by `atlas_plugin_database_schema`, deliberately independent of `Resource`'s own kind-details model and lifecycle. It is written today only through its own dedicated endpoint, `DatabaseSchemaController` (`plugins/database-schema/backend/atlas_plugin_database_schema/api/views.py`), which never invokes `EntityService`/the `Resource` kind handler — by design (`entity-facets` spec: "Facet write does not invoke the entity's kind handler").

Ingestion (`atlas_plugin_ingestion`), by contrast, is built entirely around `EntityService`: every entity write goes through `EntityService.create`/`.update`/`.revive`/`.remove` (`ingestion-plugin` spec: "All entity changes flow through the core Entity Service"). The one existing exception is Architecture Relationships (`upsert.py`'s `reconcile_declared_relationships`), which writes its own model directly in a second pass after the entity's own `EntityService`-mediated upsert — an accepted precedent for data that is related to, but not part of, an entity's own core identity/spec.

`atlas_plugin_ingestion` already has a real, working pattern for depending on functionality another plugin owns without hard-coding that dependency into its core upsert path: `atlas.ingestion.connectors.v1` and `atlas.ingestion.parsers.v1` (`extension_points.py`), keyed extension points that other code registers implementations against inside `register_runtime()` — invoked only for plugins that are actually selected/composed for the distribution.

## Goals / Non-Goals

**Goals:**
- Let a `Resource` manifest reference a `.sql` file in the repository and have ingestion keep its `DatabaseSchema` Facet in sync with it, using the same fetch/parse infrastructure ingestion already has.
- Do this without `atlas_plugin_ingestion`'s core upsert path acquiring hard-coded knowledge of `atlas_plugin_database_schema` specifically, or of facets in general beyond one small, generic extension point.
- Do this without risking a runtime failure (a write against a table that doesn't exist) in a distribution that selects `atlas.ingestion` and `atlas.standard-catalog` but not `atlas.database-schema`.
- Bring manual-write protection for a YAML-managed Resource's Facet in line with how every other kind of YAML-managed entity data already behaves.

**Non-Goals:**
- A generalized mechanism for arbitrary facet plugins to declare "my facet is also protected once its entity is YAML-managed" — this change adds that check locally, inside `atlas_plugin_database_schema` only.
- Sharing manifest-relative-path-resolution code with the sibling `add-ingestion-manifest-includes` change's `Include` mechanism — duplicated independently in this change.
- Inline SQL embedded directly in `catalog-info.yaml` — schemas are assumed to already exist as `.sql` files in the repository; `sourceSqlPath` points at one rather than duplicating its content into YAML.
- Any change to how `DatabaseSchema` is rendered (ER Diagram view) — unaffected by this change.

## Decisions

### D1: `sourceSqlPath`, resolved and fetched by ingestion, not by the facet-writer

`Resource.spec.databaseSchema.sourceSqlPath` is a path to a `.sql` file, resolved relative to the directory of the manifest file (or included fragment) that declares it. Ingestion resolves this path and calls `SourceConnector.fetch_file` itself — the registered facet-writer (D3) receives already-fetched `dialect`/`source_sql` text, never a connector or a path. This keeps "talking to the repository" exclusively inside ingestion's own connector layer, and keeps a facet-writer plugin's responsibility limited to "given this content, do something with it," matching how database-schema's own `parse_schema()` is already a pure function with no I/O.

**Alternative considered**: give the facet-writer the raw `sourceSqlPath` and let it fetch the file itself. Rejected — would require exposing `SourceConnector`/repository-fetch capability to arbitrary facet plugins, a much larger surface than a plugin should need for "parse this SQL and save it."

This resolution logic is deliberately **not** shared with the sibling `add-ingestion-manifest-includes` change's `Include.spec.paths` resolution, even though both resolve a path relative to a manifest's directory and fetch it via the same `SourceConnector.fetch_file`. A shared helper was considered and explicitly declined during exploration of this change, since there is currently exactly one consumer on each side and premature sharing would couple two otherwise-independent changes' implementation details together for no present benefit. Worth revisiting only if a third consumer of "resolve a manifest-relative repo path" appears.

### D2: A new `atlas.ingestion.facet_writers.v1` extension point, not a direct import and not a capability check

Two approaches were seriously considered and rejected before landing here:

1. **Direct import**: `atlas_plugin_ingestion.upsert` already does a module-level `from atlas_plugin_apis.contracts import ApiSpecPatch` for the `API` kind's own spec schema (`_PATCH_SCHEMAS`), with no corresponding `requires_plugins` entry for `atlas.apis` in `atlas_plugin_ingestion.plugin`. This establishes that a hard cross-plugin import is *not* unsafe in this codebase's composition model at the Python level: every plugin's backend package is always present in the environment regardless of which plugins are selected for a distribution — "selection" only controls which `django_apps` are added to `INSTALLED_APPS` (and therefore which migrations run), not whether the package is importable. So import-time failure was never the actual risk here. This approach was still rejected because `DatabaseSchema` is a Facet — optional and bolt-on by design (`entity-facets` spec) — not one of the fixed five core entity-kind spec schemas (System/Component/Resource/API/Actor) ingestion's upsert path already has to know about to do its basic job. Hard-wiring ingestion's core module to an open-ended, growing set of optional facet plugins doesn't scale the way knowing the five fixed kinds does, and it still leaves the real correctness risk (below) unsolved on its own.

2. **Gate the write with `resolve_capability(KIND_RESOURCE, SCHEMA_HOST_V1)`** — the same check `DatabaseSchemaController._get_schema_host` already uses to decide whether a kind can host this Facet at all. This looks like the obvious guard but is wrong: `SCHEMA_HOST_V1` is declared statically and unconditionally by `atlas_plugin_standard_catalog`'s `resource_handler.py` (`provides: list[str] = [SCHEMA_HOST_V1]`), independent of whether `atlas.database-schema` is selected. `resolve_capability` would return `Ok(True)` even in a distribution that never selected `atlas.database-schema`, and a subsequent write would fail on a database table that was never migrated into existence (`atlas_plugin_database_schema` wouldn't be in `INSTALLED_APPS`). **Capabilities in this codebase describe what a kind could support if some provider exists, not whether a specific provider plugin is currently selected** — this distinction is easy to get wrong and is the main reason to write it down explicitly here.

**Accepted approach**: `atlas_plugin_ingestion.extension_points` gains a new `KeyedExtensionPoint`, `atlas.ingestion.facet_writers.v1`, alongside the existing `connectors`/`parsers`. `atlas_plugin_database_schema.plugin` gains a `register_runtime()` (it currently has none at all) that registers its facet-writer under key `'database-schema'`. Because `register_runtime()` only runs for plugins actually selected/composed — the exact mechanism `atlas.ingestion`'s own `connectors`/`parsers` registration already depends on — resolving `'database-schema'` and finding nothing registered is a reliable signal that the plugin isn't active, with no capability check and no risk of hitting a missing table.

### D3: The facet-writer interface has two operations: `apply` and `clear`

```
apply(entity: CatalogEntity, dialect: str, source_sql: str) -> None
clear(entity: CatalogEntity) -> None
```

`apply` is called when a Resource's manifest declares `spec.databaseSchema`; it reuses the existing `parse_schema()` (a pure function, already used by the manual CRUD path) to populate `dialect`/`source_sql`/`parsed_schema`/`parse_status`. `clear` is called when a Resource that previously had a `databaseSchema` declaration is re-ingested without one — full-overwrite semantics (ADR 0001: a field the manifest omits is explicitly reset, not left untouched), the same principle `reconcile_declared_relationships` already applies to declared Architecture Relationships. Both are called from ingestion's pipeline in a second pass after a Resource's normal `EntityService`-mediated upsert, the same shape `reconcile_declared_relationships` already uses.

### D4: `databaseSchema` lives on an ingestion-only manifest schema, not on `ResourceSpecPatch`

`ResourceSpecPatch` (`plugins/standard-catalog/backend/atlas_plugin_standard_catalog/api/schemas.py`) backs both ingestion's full-overwrite upsert *and* the manual Resource CRUD API's partial-patch `PATCH /api/resources/{id}`. Adding `databaseSchema` to it would make it settable through the plain Resource CRUD endpoint too, which bypasses `DatabaseSchemaController` entirely (its own permission check, its own conflict handling, and — after D6 below — its own YAML-managed guard). `databaseSchema` is therefore parsed as part of ingestion's own manifest-document schema (alongside, not merged into, `ResourceSpecPatch`), read by the pipeline to drive the D2/D3 facet-writer call, and never handed to `EntityService.update` as part of the Resource's own spec patch.

### D5: `entity-facets` and `ingestion-plugin` specs are unaffected by their existing normative text

The facet write in D2/D3 still does not invoke `EntityService` or the `Resource` kind handler — `entity-facets`'s "Facet write does not invoke the entity's kind handler" requirement continues to hold exactly as written, and `ingestion-plugin`'s "all entity changes flow through the core Entity Service" requirement is about entity changes (core identity/spec), which this change does not touch for the Facet. No delta is needed against either spec's existing requirement text; a delta is added only to `database-schema-plugin` (D6).

### D6: Manual writes to a YAML-managed Resource's Facet are rejected — a narrow, explicit exception

`DatabaseSchemaController._check_write_permission` today checks only the `resource.edit` policy permission; it has no awareness of `source_kind` at all, so a YAML-managed Resource's Facet can currently be freely edited by hand. Every other kind of YAML-managed entity data in this codebase rejects manual writes unconditionally once `source_kind == SOURCE_YAML` — but that enforcement lives centrally in `EntityService` (`core/backend/server/apps/catalog/services/entity_service.py`'s `if source != CatalogEntity.SOURCE_YAML` checks), which `DatabaseSchemaController` never goes through, by design. This protection therefore does not come for free for the Facet and needs an explicit new check: reject the write if `entity.source_kind == SOURCE_YAML`.

This is scoped as a narrow, local exception — added directly inside `atlas_plugin_database_schema`'s own controller, not as a generalized "a Facet is protected once its entity is YAML-managed" mechanism other facet plugins could opt into. It does not change `entity-facets`'s general principle that a Facet's lifecycle is independent of its entity's core lifecycle; it is a `database-schema-plugin`-specific precondition on its own write endpoint. The check is unconditional on the entity's `source_kind`, not on whether the *current* manifest happens to declare `databaseSchema` this run — matching how YAML-management already behaves elsewhere (all-or-nothing at the entity level).

## Risks / Trade-offs

- **[A Resource with an existing, manually-entered Facet becomes YAML-managed later]** → Its Facet becomes immediately unwritable by hand (D6) the moment the Resource's `source_kind` flips to `yaml`, even if that manifest never declares `databaseSchema`. The previously-entered data is not deleted (only `apply`/`clear`, D3, ever touch the Facet's content, and neither runs unless `databaseSchema` is declared or was previously declared), but it becomes frozen and inaccessible to edit until/unless the manifest starts declaring `databaseSchema` for it. → No mitigation beyond documenting this clearly for operators; consistent with how YAML-management already freezes every other kind of manually-entered data on adoption.
- **[Duplicated path-resolution logic vs. the sibling `Include` change]** → Two near-identical, independently-maintained pieces of "resolve a path relative to a manifest's directory" code. → Accepted (D1); revisit only if a third consumer appears.
- **[`register_runtime()` ordering between `atlas.ingestion` and `atlas.database-schema`]** → `atlas_plugin_ingestion`'s own `register_runtime()` populates `connectors`/`parsers` on itself; `atlas_plugin_database_schema`'s new `register_runtime()` needs to register into `atlas_plugin_ingestion.extension_points.facet_writers`, which must exist (module-level, so import order doesn't matter) before either plugin's `register_runtime()` runs. → No new risk beyond what already exists for `connectors`/`parsers`: the extension-point registry objects are created at import time in `atlas_plugin_ingestion.extension_points`, independent of `register_runtime()` execution order across plugins.

## Migration Plan

1. Add `atlas.ingestion.facet_writers.v1` (`KeyedExtensionPoint`) to `atlas_plugin_ingestion.extension_points`. No migration; in-memory registry.
2. Add the ingestion-only manifest schema carrying `databaseSchema`, and wire `pipeline.py`/`upsert.py` to call `facet_writers.resolve('database-schema')` (a no-op if nothing is registered) after a Resource's normal upsert.
3. Implement `atlas_plugin_database_schema`'s `register_runtime()` and its `apply`/`clear` facet-writer, reusing `parse_schema()`.
4. Add the `source_kind == SOURCE_YAML` check to `DatabaseSchemaController._check_write_permission`.
5. Rollback: reverting steps 1-3 leaves `DatabaseSchema` exactly as it works today (manual-only). Reverting step 4 alone (if the manual-write rejection proves too disruptive before the rest ships) is independent and safe to do separately.

## Open Questions

- Should the manual-write rejection in D6 (step 4) ship gated behind the rest of this change being complete, or could it ship first/independently, ahead of ingestion actually being able to populate the Facet? Shipping it first would freeze existing manually-entered Facets on already-YAML-managed Resources before ingestion offers any way to manage them — probably undesirable; likely ship together or gate step 4 behind the whole change being available.
- Exact shape of the ingestion-only manifest schema from D4 (a nested Pydantic model on the manifest's own `ResourceIn`-equivalent, vs. a separate top-level structure) is left to implementation — no behavioral question, just where the type lives.
