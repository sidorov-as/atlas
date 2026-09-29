## ADDED Requirements

### Requirement: Catalog-wide System Landscape is generated from architecture data
The system SHALL generate a PlantUML-backed System Context Diagram for the entire catalog. It SHALL include every catalog System, include Users and Groups only when they are explicit Architecture Relationship endpoints, map System-bound relationship endpoints to their owning System, and combine declared Architecture Relationships with cross-system derived catalog interactions. A declared interaction SHALL supersede a derived fallback with the same directed visible endpoints.

#### Scenario: Landscape includes all systems and explicit people
- **WHEN** the catalog contains Systems and a User with an explicit Architecture Relationship to a Component
- **THEN** the System Landscape contains every System, the User as a C4 Person, and the User's relationship to the Component's System

#### Scenario: Landscape does not infer actors from ownership
- **WHEN** a User owns or belongs to a Group that owns catalog entities but has no explicit Architecture Relationship
- **THEN** the User and Group do not appear in the System Landscape

### Requirement: Catalog-wide System Landscape is served as an image
The diagram endpoint SHALL serve the catalog-wide System Landscape as SVG by default and support PNG and download behavior equivalent to existing diagram endpoints.

#### Scenario: User requests the default landscape image
- **WHEN** an authenticated user requests the System Landscape without a format parameter
- **THEN** the endpoint returns generated `image/svg+xml` content without requiring an entity id

#### Scenario: User downloads a PNG landscape image
- **WHEN** an authenticated user requests the System Landscape with `format=png` and download enabled
- **THEN** the endpoint returns an `image/png` attachment

## MODIFIED Requirements

### Requirement: Atlas C4 diagrams use stable top-down semantic styling
The system SHALL render System Context, System Architecture, Component, and System Landscape diagrams with `LAYOUT_TOP_DOWN`, a visible Atlas legend, fixed rounded semantic element styles, and fixed relationship styles. Element styles SHALL include role-specific background, font, border color, border style, border thickness, and deliberate shadowing. Explicit Architecture Relationship interaction kinds SHALL map to distinct solid, dashed, or dotted relationship tags; derived fallback edges SHALL use a distinct derived tag. Free-form catalog metadata tags SHALL not change generated diagram styling.

#### Scenario: Interaction kinds are visually distinguished
- **WHEN** a diagram contains synchronous, asynchronous, data-access, and manual Architecture Relationships
- **THEN** its rendered PlantUML model assigns a stable distinct color, line treatment, and legend entry to each interaction kind

#### Scenario: Diagram elements use rounded semantic roles
- **WHEN** a diagram contains an internal component, database, queue, and external endpoint
- **THEN** each renders as a rounded semantic role with the approved fixed palette and legend treatment

#### Scenario: Catalog metadata cannot arbitrarily restyle a diagram
- **WHEN** an entity has free-form catalog tags that are not Atlas diagram role tags
- **THEN** those tags do not change the generated PlantUML styling
