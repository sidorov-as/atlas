## MODIFIED Requirements

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
