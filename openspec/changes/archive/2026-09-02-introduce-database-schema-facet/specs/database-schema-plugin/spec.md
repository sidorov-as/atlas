## ADDED Requirements

### Requirement: Resource may carry a Database Schema facet
A Resource entity SHALL be able to carry a `DatabaseSchema` Facet storing `dialect`, `source_sql`, a parsed schema structure, and a parse status.

#### Scenario: Attaching a schema to a Resource
- **WHEN** a user attaches PostgreSQL `source_sql` to a Resource
- **THEN** the facet stores the SQL, its dialect, and the parsed schema structure

### Requirement: A failed parse preserves the saved SQL
A `source_sql` edit that fails to parse SHALL still be saved, with `parse_status` set to failed, rather than being rejected.

#### Scenario: Malformed SQL is saved with a failure indicator
- **WHEN** a user saves `source_sql` that fails to parse
- **THEN** the facet stores the submitted SQL text, sets `parse_status` to failed, and the UI shows a visible parse-failure indicator

### Requirement: ER Diagram view is derived from the parsed schema
When a Resource's `DatabaseSchema` facet has a successfully parsed schema, an ER Diagram view SHALL render it, gated by the `schema.host.v1` entity capability rather than a hard-coded kind check.

#### Scenario: ER Diagram tab appears for a schema-bearing Resource
- **WHEN** a Resource has a `DatabaseSchema` facet with `parse_status` ok
- **THEN** its detail page shows an ER Diagram tab rendering the parsed schema

#### Scenario: No ER Diagram tab without a facet
- **WHEN** a Resource has no `DatabaseSchema` facet
- **THEN** its detail page shows no ER Diagram tab

### Requirement: Database Schema is an optional plugin
A distribution MAY omit `atlas.database-schema`; Resources SHALL continue to function normally without it.

#### Scenario: Distribution without the plugin composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.database-schema`
- **THEN** composition succeeds, and Resource entities show no schema editor or ER Diagram tab
