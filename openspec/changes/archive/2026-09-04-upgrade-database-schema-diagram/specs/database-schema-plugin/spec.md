## MODIFIED Requirements

### Requirement: Resource may carry a Database Schema facet
A Resource entity SHALL be able to carry a `DatabaseSchema` Facet storing a user-selected `dialect` (PostgreSQL, MySQL, or MS SQL), `source_sql`, a tbls-compatible parsed schema structure, and a parse status. The dialect SHALL be selectable on the same Schema tab where `source_sql` is edited, and saved together with it.

#### Scenario: Attaching a schema to a Resource
- **WHEN** a user selects a dialect and attaches `source_sql` to a Resource
- **THEN** the facet stores the SQL, the selected dialect, and the parsed schema structure

#### Scenario: Selecting a non-default dialect
- **WHEN** a user selects MySQL or MS SQL as the dialect before saving `source_sql`
- **THEN** the facet parses the SQL using that dialect and stores the result

### Requirement: A failed parse preserves the saved SQL
A `source_sql` edit that fails to parse SHALL still be saved, with `parse_status` set to failed, rather than being rejected.

#### Scenario: Malformed SQL is saved with a failure indicator
- **WHEN** a user saves `source_sql` that fails to parse
- **THEN** the facet stores the submitted SQL text, sets `parse_status` to failed, and the UI shows a visible parse-failure indicator

#### Scenario: ER Diagram tab shows an error banner for a failed parse
- **WHEN** a Resource's `DatabaseSchema` facet has `parse_status` failed
- **THEN** its ER Diagram tab shows a visible error banner instead of a diagram, rather than silently omitting the tab's content

### Requirement: ER Diagram view is derived from the parsed schema
When a Resource's `DatabaseSchema` facet has a successfully parsed schema, an ER Diagram view SHALL render it as a read-only, pannable and zoomable graph — with table nodes, relation edges, drag-to-reposition, zoom in/out, fit-to-viewport, and SVG/PNG export — gated by the `schema.host.v1` entity capability rather than a hard-coded kind check.

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

#### Scenario: Exporting the diagram
- **WHEN** a user chooses to export the ER Diagram
- **THEN** the system provides the current diagram as a downloadable SVG file and as a downloadable PNG file
