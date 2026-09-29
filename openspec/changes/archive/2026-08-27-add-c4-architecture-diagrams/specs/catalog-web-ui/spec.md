## MODIFIED Requirements

### Requirement: Entity detail pages
System, Component, Resource, and API SHALL each have a detail page with an Overview and Relations view; System and Component detail pages SHALL additionally show their C4 Diagram tab and (for System) Components/Resources/APIs/Docs tabs. An API detail page SHALL additionally show a Documentation tab when its `type` has a documentation viewer available. System and Component C4 Diagram tabs SHALL render their diagram in a full-width viewer outside the normal right-rail layout.

#### Scenario: System detail shows its tabs
- **WHEN** a user opens a System's detail page
- **THEN** it shows Overview, Components, Resources, APIs, Docs, Relations, and C4 Diagram tabs

#### Scenario: Component detail shows its tabs
- **WHEN** a user opens a Component's detail page
- **THEN** it shows Overview, Relations, and C4 Diagram (component view) tabs, but no Components/Resources/APIs/Docs tabs

#### Scenario: Resource detail shows only Overview and Relations
- **WHEN** a user opens a Resource's detail page
- **THEN** it shows only Overview and Relations tabs, with no C4 Diagram tab

#### Scenario: API detail shows Overview, Relations, and conditionally Documentation
- **WHEN** a user opens an API's detail page
- **THEN** it shows Overview and Relations tabs, with no C4 Diagram tab, and additionally shows a Documentation tab only when the API's `type` is `openapi` or `asyncapi`

#### Scenario: C4 Diagram uses full available page width
- **WHEN** a user opens the C4 Diagram tab for a System or Component
- **THEN** the viewer occupies the detail page width that would otherwise be divided between the content column and right rail

## ADDED Requirements

### Requirement: Diagram viewer provides viewport controls and download
The System and Component C4 Diagram viewer SHALL provide pointer pan, Zoom in, Zoom out, Fit to viewport, and an image download action. It SHALL show loading and rendering-failure states without leaving a broken image element.

#### Scenario: User fits a zoomed diagram
- **WHEN** a user changes the diagram scale and activates Fit to viewport
- **THEN** the diagram returns to a scale and position that fits its viewer bounds

#### Scenario: User downloads the visible diagram format
- **WHEN** a user activates the diagram download action
- **THEN** the browser requests the same diagram endpoint with download enabled and receives an image attachment

### Requirement: Relations tab manages declared architecture relationships separately
The Relations tab SHALL show derived Catalog relations and declared Architecture Relationships in separate labeled sections. A manual entity's Architecture Relationships section SHALL provide create, edit, and delete controls for outgoing manual relationships; YAML-origin relationships SHALL be visibly read-only.

#### Scenario: Manual entity adds an architecture relationship
- **WHEN** a user with edit access opens a manual Component's Relations tab and creates an outgoing Architecture Relationship
- **THEN** the relationship appears in the Architecture Relationships section without changing the Catalog relations section

#### Scenario: YAML relationship is displayed as read-only
- **WHEN** a user views a YAML-managed entity's Architecture Relationships section
- **THEN** declared relationships are visible with their label, technology, interaction kind, and target but no edit or delete control
