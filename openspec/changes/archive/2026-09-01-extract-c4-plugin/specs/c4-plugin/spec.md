## ADDED Requirements

### Requirement: C4 is an optional plugin targeting a capability, not a kind list
C4 diagram generation, viewing, and preferences SHALL be provided entirely by the `atlas.c4` plugin, and SHALL apply to entities by their declared `architecture.subject.v1` (boxed diagram subject) or `architecture.actor.v1` (C4 Person) capability rather than a hard-coded kind check.

#### Scenario: A capability-declaring actor renders as a Person
- **WHEN** an Architecture Relationship's endpoint is an entity whose kind declares `architecture.actor.v1`
- **THEN** the diagram renders that endpoint as a C4 Person, without the diagram builder naming the endpoint's kind explicitly

#### Scenario: Distribution without atlas.c4 composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.c4`
- **THEN** composition succeeds, no diagram endpoints are registered, and no C4 tab or home widget appears

#### Scenario: Diagram tab appears only for capable entities
- **WHEN** `atlas.c4` is installed
- **THEN** its detail tab appears only on entities of a kind declaring `architecture.subject.v1`

### Requirement: Diagram access requires a registered permission
Reading a diagram SHALL require the `atlas.c4.diagram.read` permission, evaluated by the deployment's configured policy evaluator.

#### Scenario: Unauthenticated diagram request is rejected
- **WHEN** a request with no authenticated session requests a diagram endpoint
- **THEN** the request is rejected before any diagram is rendered

### Requirement: Home widget shows the catalog-wide landscape
The C4 plugin SHALL contribute a home-page widget rendering the catalog-wide System Landscape diagram.

#### Scenario: Home page shows the landscape widget
- **WHEN** a logged-in user with `atlas.c4` installed opens the home page
- **THEN** the page shows a widget rendering the System Landscape diagram
