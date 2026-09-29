## MODIFIED Requirements

### Requirement: C4 is an optional plugin targeting a capability, not a kind list
C4 diagram generation, viewing, and preferences SHALL be provided entirely by the `atlas.c4` plugin, and SHALL apply to entities by their declared `architecture.subject.v1` (boxed diagram subject) or `architecture.actor.v1` (C4 Person) capability rather than a hard-coded kind check.

#### Scenario: A capability-declaring actor renders as a Person
- **WHEN** an Architecture Relationship's endpoint is an entity whose kind declares `architecture.actor.v1`
- **THEN** the diagram renders that endpoint as a C4 Person, without the diagram builder naming the endpoint's kind explicitly

#### Scenario: Distribution without atlas.c4 composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.c4`
- **THEN** composition succeeds, no diagram endpoints are registered, and no C4 tab or "System Map" nav item appears

#### Scenario: Diagram tab appears only for capable entities
- **WHEN** `atlas.c4` is installed
- **THEN** its detail tab appears only on entities of a kind declaring `architecture.subject.v1`

## REMOVED Requirements

### Requirement: Home widget shows the catalog-wide landscape
The C4 plugin SHALL contribute a home-page widget rendering the catalog-wide System Landscape diagram.

#### Scenario: Home page shows the landscape widget
- **WHEN** a logged-in user with `atlas.c4` installed opens the home page
- **THEN** the page shows a widget rendering the System Landscape diagram

**Reason**: The System Landscape diagram moves off the homepage into its own nav destination — see the new "System Map is a dedicated nav destination" requirement below.
**Migration**: No data or backend change; only the frontend contribution type changes, from a `homeWidget` to a `route` + `navItem`.

## ADDED Requirements

### Requirement: System Map is a dedicated nav destination
The `atlas.c4` plugin SHALL contribute its own "System Map" route and navigation item rendering the catalog-wide System Landscape diagram, rather than a homepage widget. When the catalog has zero System entities, the page SHALL show an empty-state message instead of attempting to render the diagram.

#### Scenario: System Map renders the landscape diagram
- **WHEN** a logged-in user with `atlas.c4` installed opens the "System Map" nav item
- **THEN** the page shows the System Landscape diagram with its pan, zoom, fit-to-viewport, SVG download, and PNG download controls

#### Scenario: System Map shows an empty state with no Systems
- **WHEN** a logged-in user opens "System Map" and the catalog has zero System entities
- **THEN** the page shows a message explaining that System Map appears once the catalog has systems, instead of rendering a diagram

#### Scenario: System Map renders systems with no relationships
- **WHEN** the catalog has at least one System entity but no authored Architecture Relationships
- **THEN** the page renders the diagram showing each System as an unconnected node, not the empty state
