## Purpose

Defines the Database Schema plugin (`atlas.database-schema`): an optional plugin that lets a Resource carry a `DatabaseSchema` Facet (dialect, source SQL, parsed schema, parse status) and renders it as a computed ER Diagram view. It is the proof point for the Facet/view split described in `plugin-architecture.md`.
## Requirements
### Requirement: Resource may carry a Database Schema facet
A Resource entity SHALL be able to carry a `DatabaseSchema` Facet storing a user-selected `dialect` (PostgreSQL, MySQL, or MS SQL), `source_sql`, a tbls-compatible parsed schema structure, and a parse status. The dialect SHALL be selectable on the same Schema tab where `source_sql` is edited, and saved together with it. `source_sql` SHALL be bounded to a fixed maximum length.

#### Scenario: Attaching a schema to a Resource
- **WHEN** a user selects a dialect and attaches `source_sql` to a Resource
- **THEN** the facet stores the SQL, the selected dialect, and the parsed schema structure

#### Scenario: Selecting a non-default dialect
- **WHEN** a user selects MySQL or MS SQL as the dialect before saving `source_sql`
- **THEN** the facet parses the SQL using that dialect and stores the result

#### Scenario: Oversized source_sql is rejected
- **WHEN** a user attempts to save `source_sql` longer than its declared maximum length
- **THEN** the request is rejected with a validation error and the facet's stored `source_sql` is unchanged

### Requirement: A failed parse preserves the saved SQL
A `source_sql` edit that fails to parse SHALL still be saved, with `parse_status` set to failed, rather than being rejected.

#### Scenario: Malformed SQL is saved with a failure indicator
- **WHEN** a user saves `source_sql` that fails to parse
- **THEN** the facet stores the submitted SQL text, sets `parse_status` to failed, and the UI shows a visible parse-failure indicator

#### Scenario: ER Diagram tab shows an error banner for a failed parse
- **WHEN** a Resource's `DatabaseSchema` facet has `parse_status` failed
- **THEN** its ER Diagram tab shows a visible error banner instead of a diagram, rather than silently omitting the tab's content

### Requirement: ER Diagram view is derived from the parsed schema
When a Resource's `DatabaseSchema` facet has a successfully parsed schema, an ER Diagram view SHALL render it as a read-only, pannable and zoomable graph — with table nodes, relation edges, drag-to-reposition, zoom in/out, fit-to-viewport, and an Export control — gated by the `schema.host.v1` entity capability rather than a hard-coded kind check.

#### Scenario: ER Diagram tab appears for a schema-bearing Resource
- **WHEN** a Resource has a `DatabaseSchema` facet with `parse_status` ok
- **THEN** its detail page shows an ER Diagram tab rendering the parsed schema as a graph

#### Scenario: No ER Diagram tab without a facet
- **WHEN** a Resource has no `DatabaseSchema` facet
- **THEN** its detail page shows no ER Diagram tab

#### Scenario: Viewer supports zoom and fit-to-viewport
- **WHEN** a user opens the ER Diagram tab for a schema-bearing Resource
- **THEN** the user can zoom in, zoom out, and fit the diagram to the viewport using on-screen controls

#### Scenario: Viewer supports repositioning without editing
- **WHEN** a user drags a table node in the ER Diagram view
- **THEN** the node moves to the new position, and no table, column, or relation is added, removed, or modified

#### Scenario: Opening the Export control shows default options
- **WHEN** a user activates the Export control on the ER Diagram tab
- **THEN** a popup opens offering an SVG/PNG format choice defaulted to SVG, a "Transparent background" checkbox defaulted to checked, and a "Grid" checkbox defaulted to checked

#### Scenario: Exporting the diagram with default options
- **WHEN** a user opens the Export control and activates the Export action without changing any option
- **THEN** the system downloads the current diagram as an SVG file with a transparent background and the grid included

#### Scenario: Exporting with a white background and no grid
- **WHEN** a user unchecks "Transparent background" and unchecks "Grid" before activating Export
- **THEN** the downloaded file has a white background and omits the grid dots, in either SVG or PNG format

#### Scenario: Export options do not affect the live viewer
- **WHEN** a user unchecks "Grid" or "Transparent background" in the Export popup, with or without completing an export
- **THEN** the ER Diagram tab's on-screen canvas continues to show its grid and background unchanged throughout

#### Scenario: Export options reset on next open
- **WHEN** a user changes the format, transparency, or grid option, exports or closes the popup, and later reopens the Export control
- **THEN** the popup shows the default format (SVG), transparent background checked, and grid checked, regardless of the previous export's choices

### Requirement: Database Schema is an optional plugin
A distribution MAY omit `atlas.database-schema`; Resources SHALL continue to function normally without it.

#### Scenario: Distribution without the plugin composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.database-schema`
- **THEN** composition succeeds, and Resource entities show no schema editor or ER Diagram tab

### Requirement: Schema editor shows SQL syntax highlighting
The Database Schema facet's `source_sql` editor SHALL render its content with SQL syntax highlighting, using generic SQL tokenization regardless of the selected dialect (PostgreSQL, MySQL, or MS SQL). Selecting a dialect SHALL continue to affect only save and parse behavior, not highlighting.

#### Scenario: SQL editor highlights syntax
- **WHEN** a user opens the Schema tab for a Resource and types `source_sql`
- **THEN** the editor renders the SQL with syntax highlighting

#### Scenario: Highlighting is unaffected by dialect selection
- **WHEN** a user switches the selected dialect between PostgreSQL, MySQL, and MS SQL
- **THEN** the SQL editor's highlighting is unchanged, and only save/parse behavior reflects the selected dialect

### Requirement: A YAML-managed Resource's Database Schema facet cannot be edited manually
Once a Resource entity is YAML-managed (`source_kind` is YAML), its `DatabaseSchema` Facet SHALL NOT be created or updated through the plugin's manual write endpoint, regardless of whether that Resource's current manifest declares `spec.databaseSchema`.

#### Scenario: Manual write is rejected on a YAML-managed Resource
- **WHEN** a user attempts to create or update the `DatabaseSchema` facet of a YAML-managed Resource through the plugin's write endpoint
- **THEN** the request is rejected and the facet's stored data is unchanged

#### Scenario: Manual write still succeeds on a non-YAML-managed Resource
- **WHEN** a user attempts to create or update the `DatabaseSchema` facet of a Resource that is not YAML-managed
- **THEN** the write succeeds as before

#### Scenario: A previously-attached facet is frozen once its Resource becomes YAML-managed
- **WHEN** a Resource with a manually-attached `DatabaseSchema` facet later becomes YAML-managed, whether or not its manifest declares `spec.databaseSchema`
- **THEN** the facet's existing data is not deleted by that transition alone, but further manual writes to it are rejected

