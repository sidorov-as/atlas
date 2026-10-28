# c4-plugin Specification

## Purpose

Defines the C4 plugin as an optional plugin that applies to entities by declared capability rather than a fixed list of kinds, gates diagram access behind a registered permission, and provides the System Map navigation destination.

## Requirements

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

### Requirement: Diagram access requires a registered permission
Reading a diagram SHALL require the `atlas.c4.diagram.read` permission, evaluated by the deployment's configured policy evaluator.

#### Scenario: Unauthenticated diagram request is rejected
- **WHEN** a request with no authenticated session requests a diagram endpoint
- **THEN** the request is rejected before any diagram is rendered

### Requirement: System Map is a dedicated nav destination
The `atlas.c4` plugin SHALL contribute its own "System Map" route and navigation item, rather than a homepage widget. The System Map page SHALL contain two tabs: Landscape, which renders the catalog-wide System Landscape diagram, and Views, which lists saved views and leads to their detail and editor pages. Landscape SHALL be the tab shown by default. When the catalog has zero System entities, the Landscape tab SHALL show an empty-state message instead of attempting to render the diagram.

#### Scenario: System Map renders the landscape diagram
- **WHEN** a logged-in user with `atlas.c4` installed opens the "System Map" nav item
- **THEN** the Landscape tab is shown with the System Landscape diagram and its pan, zoom, fit-to-viewport, SVG download, and PNG download controls

#### Scenario: System Map shows an empty state with no Systems
- **WHEN** a logged-in user opens "System Map" and the catalog has zero System entities
- **THEN** the Landscape tab shows a message explaining that System Map appears once the catalog has systems, instead of rendering a diagram

#### Scenario: System Map renders systems with no relationships
- **WHEN** the catalog has at least one System entity but no authored Architecture Relationships
- **THEN** the Landscape tab renders the diagram showing each System as an unconnected node, not the empty state

#### Scenario: Views is a second tab
- **WHEN** a logged-in user opens "System Map"
- **THEN** a Views tab is available next to Landscape, and selecting it shows the saved views list without changing the Landscape diagram or its controls

#### Scenario: A Views link opens the Views tab
- **WHEN** a user opens a System Map URL that identifies the Views tab
- **THEN** the page opens on the Views tab instead of Landscape

#### Scenario: Navigation item stays active on view pages
- **WHEN** a user is on a view detail or editor page
- **THEN** the System Map navigation item is shown as active
