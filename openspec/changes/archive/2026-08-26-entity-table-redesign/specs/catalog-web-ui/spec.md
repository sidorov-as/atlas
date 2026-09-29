## MODIFIED Requirements

### Requirement: Entity list preview panel
System, Component, Resource, API, and Team list pages SHALL open a right-side preview panel when a row is clicked, showing a summary of that entity with a link-through action to its full detail page, instead of navigating away immediately. The link-through action SHALL be a small icon-button in the panel's header row, next to the entity title, rather than a full-width button. A second, fast click on a row that is already open in the preview panel SHALL additionally navigate to that entity's full detail page, without introducing any delay to the panel opening on the first click of any row.

#### Scenario: Clicking a row opens the preview panel
- **WHEN** a user clicks a row in any of the five entity list pages (Systems, Components, Resources, APIs, Teams)
- **THEN** a right-side panel opens showing that entity's summary, and the underlying list remains visible

#### Scenario: Preview panel links through to the full detail page
- **WHEN** a user clicks the icon-button next to the entity title in the preview panel's header
- **THEN** they are navigated to that entity's full detail page

#### Scenario: Preview panel can be dismissed without navigating
- **WHEN** a user closes the preview panel (e.g. via a close control)
- **THEN** the panel closes, the user remains on the list page, and no navigation has occurred

#### Scenario: A fast second click on the open row navigates to its detail page
- **WHEN** a user clicks a row, the preview panel opens for it, and the user clicks that same row again within the double-click window
- **THEN** they are navigated to that entity's full detail page

#### Scenario: The first click on any row is never delayed
- **WHEN** a user clicks a row for the first time
- **THEN** the preview panel opens immediately, with no debounce or waiting period to see whether a second click follows

### Requirement: Consistent entity table width
Every table rendered via the shared entity table component SHALL be capped at a maximum width, shrinking to fit its container when narrower than that cap, rather than always stretching to fill the full width of its containing column.

#### Scenario: A table narrower than the cap fits its column
- **WHEN** a table's containing column is narrower than the configured maximum width
- **THEN** the table renders at the column's width, same as before

#### Scenario: A table in a wide column does not exceed the cap
- **WHEN** a table's containing column is wider than the configured maximum width (e.g. on a wide viewport with no preview panel open)
- **THEN** the table renders at the maximum width, not the full column width

## ADDED Requirements

### Requirement: Row-level Edit and Remove actions
Every row in the Systems, Components, Resources, APIs, and Teams list tables SHALL offer a context-actions control with exactly two entries: Edit and Remove. For Systems, Components, Resources, and APIs, this control SHALL be omitted entirely on rows for YAML-managed (non-manual) entities, matching the same manual/YAML-managed distinction already used to show or hide Add/Edit affordances on those entities' detail pages. Team rows SHALL always show the control, since Teams cannot be YAML-managed.

#### Scenario: Manual entity row shows Edit and Remove
- **WHEN** a user views a list row for a manually-managed System, Component, Resource, or API
- **THEN** its context-actions control offers exactly two entries: Edit and Remove

#### Scenario: YAML-managed entity row shows no actions control
- **WHEN** a user views a list row for a System, Component, Resource, or API ingested from a YAML source
- **THEN** no context-actions control is shown for that row

#### Scenario: Team row always shows Edit and Remove
- **WHEN** a user views a row in the Teams list table
- **THEN** its context-actions control offers exactly two entries: Edit and Remove, regardless of that Team's origin

#### Scenario: Activating a row action does not also open the preview panel
- **WHEN** a user clicks Edit or Remove in a row's context-actions control
- **THEN** only that action's handler runs; the row's preview-panel-opening click behavior does not also fire

### Requirement: Borderless entity table framing
Every table rendered via the shared entity table component SHALL render without a border or rounded-corner frame around the table itself. Where a page shows more than one such table in the same column (e.g. a Team's owned-entity sections), the tables SHALL be visually separated by spacing and their existing section subheadings, not by a card boundary around each table.

#### Scenario: A single table has no border or rounded corners
- **WHEN** a user views any entity list, detail-page sub-table, or reference table in the catalog
- **THEN** no border or rounded-corner frame is drawn around the table

#### Scenario: Stacked tables on the same page are separated by spacing, not boxes
- **WHEN** a page shows multiple tables in the same column, one after another
- **THEN** each is preceded by its own section subheading and separated by spacing from the one before it, with no card boundary drawn around any individual table
