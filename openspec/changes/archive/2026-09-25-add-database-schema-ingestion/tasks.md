## 1. `facet_writers` extension point

- [x] 1.1 Add `atlas.ingestion.facet_writers.v1` as a new `KeyedExtensionPoint` in `plugins/ingestion/backend/atlas_plugin_ingestion/extension_points.py`, alongside the existing `connectors`/`parsers`.
- [x] 1.2 Define the facet-writer protocol/interface (`apply(entity, dialect, source_sql) -> None`, `clear(entity) -> None`).

## 2. Manifest schema and path resolution

- [x] 2.1 Add the ingestion-only manifest schema carrying `spec.databaseSchema: {dialect, sourceSqlPath}` for the `Resource` kind (not merged into `ResourceSpecPatch`, per design.md D4).
- [x] 2.2 Implement `sourceSqlPath` resolution relative to the declaring manifest's own directory (independent implementation from the sibling `add-ingestion-manifest-includes` change's `Include` path resolution — do not share code, per design.md D1).
- [x] 2.3 Fetch the resolved path's content via the existing `SourceConnector.fetch_file`.

## 3. Pipeline integration

- [x] 3.1 After a Resource's normal `EntityService`-mediated upsert, if `spec.databaseSchema` is declared, resolve `facet_writers.resolve('database-schema')` and call `apply(entity, dialect, source_sql)` if a writer is registered (no-op otherwise).
- [x] 3.2 If a Resource previously had `spec.databaseSchema` declared and the current re-ingestion no longer declares it, call the registered writer's `clear(entity)`.
- [x] 3.3 Isolate failures the same way other per-manifest failures are isolated (a fetch failure for `sourceSqlPath`, or an absent facet writer, must not block the rest of that Resource's own upsert or the rest of the run).

## 4. `atlas_plugin_database_schema` facet-writer implementation

- [x] 4.1 Add `register_runtime()` to `plugins/database-schema/backend/atlas_plugin_database_schema/plugin.py` (currently absent), registering this plugin's facet-writer under key `'database-schema'` against `atlas_plugin_ingestion.extension_points.facet_writers`.
- [x] 4.2 Implement `apply`: reuse the existing `parse_schema()` from `parser.py` to populate `dialect`/`source_sql`/`parsed_schema`/`parse_status` on the `DatabaseSchema` Facet, creating it if absent.
- [x] 4.3 Implement `clear`: remove or reset the `DatabaseSchema` Facet for the given entity.

## 5. Manual-write protection

- [x] 5.1 Add a `source_kind == SOURCE_YAML` check to `DatabaseSchemaController._check_write_permission` in `plugins/database-schema/backend/atlas_plugin_database_schema/api/views.py`, rejecting `POST`/`PATCH` on a YAML-managed Resource's facet.
- [x] 5.2 Confirm `GET` (read) remains unaffected — only write endpoints reject.

## 6. Tests

- [x] 6.1 Unit tests for `facet_writers` extension point: registration, resolution, no-op when nothing registered.
- [x] 6.2 Unit tests for `sourceSqlPath` resolution (relative to declaring manifest's directory) and fetch-failure isolation.
- [x] 6.3 Unit tests for `apply`/`clear`: first ingestion creates the facet, re-ingestion with changed content updates it in place, dropping the declaration clears it.
- [x] 6.4 Integration test: a repository with a Resource manifest declaring `spec.databaseSchema` ends up with a populated, correctly-parsed `DatabaseSchema` facet after a run.
- [x] 6.5 Integration test: the same run against a distribution that does not select `atlas.database-schema` still successfully ingests the Resource's own fields, with no facet write attempted and no error.
- [x] 6.6 Test: manual `POST`/`PATCH` to `DatabaseSchemaController` is rejected once the target Resource is YAML-managed, and still succeeds for a non-YAML-managed Resource.
- [x] 6.7 Regression test: existing manual Facet CRUD behavior for non-YAML-managed Resources is unchanged.

## 7. Documentation

- [x] 7.1 Document the `spec.databaseSchema` manifest field and its `sourceSqlPath` resolution rule (`docs-site/docs/features/ingestion.md` and/or `docs-site/docs/plugin-development/built-in/ingestion.md`).
- [x] 7.2 Document the manual-write-rejection behavior change for YAML-managed Resources in the Database Schema plugin's own docs, including the "previously-attached facet is frozen" edge case from design.md's Risks section.
