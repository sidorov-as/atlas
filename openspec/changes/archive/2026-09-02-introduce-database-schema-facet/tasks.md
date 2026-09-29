## 1. Scaffold and model

- [x] 1.1 Create `plugins/database-schema/backend/` and `plugins/database-schema/frontend/` declaring a manifest dependency on `atlas.standard-catalog`.
- [x] 1.2 Add the `DatabaseSchema` model (`OneToOneField(CatalogEntity, primary_key=True)`: `dialect`, `source_sql`, `parsed_schema`, `parse_status`) and migration.
- [x] 1.3 Declare `schema.host.v1` on the `resource` kind's registration in Standard Catalog.

## 2. Parsing and API

- [x] 2.1 Implement the PostgreSQL-dialect SQL parser producing `parsed_schema`.
- [x] 2.2 Implement `GET/POST/PATCH /api/plugins/atlas.database-schema/resources/{entityId}/schema`, saving `source_sql` unconditionally and setting `parse_status` from the parse attempt.
- [x] 2.3 Test the failed-parse-preserves-input path explicitly.

## 3. Frontend

- [x] 3.1 Add the schema editor (SQL input) contribution on Resource's detail page.
- [x] 3.2 Add the ER Diagram tab contribution, gated by `entitySupports('schema.host.v1')`, rendering from `parsed_schema`.
- [x] 3.3 Add the parse-failure indicator to the editor.

## 4. Verify

- [x] 4.1 Attach a schema to a Resource; verify the ER Diagram tab renders it.
- [x] 4.2 Verify a failed-parse SQL edit is saved with a visible failure indicator, not rejected.
- [x] 4.3 Delete the facet; verify the Resource's own core/kind data is unaffected.
- [x] 4.4 Compose a distribution without `atlas.database-schema`; verify Resources show no editor or ER Diagram tab.
