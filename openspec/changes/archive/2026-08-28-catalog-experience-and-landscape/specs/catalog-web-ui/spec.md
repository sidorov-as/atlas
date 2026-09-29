## MODIFIED Requirements

### Requirement: Entity list preview panel
System, Component, Resource, API, and Team list pages SHALL render their heading and description before a shared table-and-preview content row. A right-side preview panel SHALL open when a row is clicked, showing a summary of that entity with a link-through action to its full detail page, instead of navigating away immediately. The link-through action SHALL be a small icon-button in the panel's header row, next to the entity title, rather than a full-width button. A second, fast click on a row that is already open in the preview panel SHALL additionally navigate to that entity's full detail page, without introducing any delay to the panel opening on the first click of any row.

#### Scenario: Clicking a row opens a table-aligned preview panel
- **WHEN** a user clicks a row in any of the five entity list pages (Systems, Components, Resources, APIs, Teams)
- **THEN** a right-side panel opens beside the table content, below the page heading and description, while the underlying list remains visible

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

### Requirement: Relations tab manages declared architecture relationships separately
The Relations tab SHALL show derived Catalog relations and declared Architecture Relationships in separate labeled sections. Its Architecture Relationships section SHALL show every declared relationship for which the current entity is either source or target, preserving the canonical directed source and target. A manual entity's Architecture Relationships section SHALL provide create, edit, and delete controls only for outgoing manual relationships whose source is that entity; YAML-origin relationships and incoming relationships SHALL be visibly read-only.

#### Scenario: Manual entity adds an outgoing architecture relationship
- **WHEN** a user with edit access opens a manual Component's Relations tab and creates an outgoing Architecture Relationship
- **THEN** the relationship appears in the Architecture Relationships section without changing the Catalog relations section

#### Scenario: Target entity sees an incoming architecture relationship
- **WHEN** a Component is the target of an Architecture Relationship from another Component
- **THEN** its Relations tab displays the relationship with its source and target direction and no edit or delete control

#### Scenario: YAML relationship is displayed as read-only
- **WHEN** a user views a YAML-managed entity's Architecture Relationships section
- **THEN** declared relationships are visible with their source, target, label, technology, interaction kind, and origin but no edit or delete control
