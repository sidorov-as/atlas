## ADDED Requirements

### Requirement: System Architecture images have a validated endpoint
The diagram endpoint SHALL accept `GET /api/diagrams/system/{id}/?view=architecture` and return a generated image in the same SVG-default, PNG, and download formats supported by the existing diagram endpoints.

#### Scenario: System Architecture defaults to SVG
- **WHEN** an authenticated user requests an existing System with `view=architecture`
- **THEN** the endpoint returns generated `image/svg+xml` content

### Requirement: Atlas C4 diagrams use stable top-down semantic styling
The system SHALL render System Context, System Architecture, and Component diagrams with `LAYOUT_TOP_DOWN`, a visible Atlas legend, fixed element-role styles, and fixed relationship styles. Explicit Architecture Relationship interaction kinds SHALL map to distinct relationship tags; derived fallback edges SHALL use a distinct derived tag.

#### Scenario: Interaction kinds are visually distinguished
- **WHEN** a diagram contains synchronous, asynchronous, data-access, and manual Architecture Relationships
- **THEN** its rendered PlantUML model assigns a stable distinct tag and legend entry to each interaction kind

#### Scenario: Catalog metadata cannot arbitrarily restyle a diagram
- **WHEN** an entity has free-form catalog tags that are not Atlas diagram role tags
- **THEN** those tags do not change the generated PlantUML styling

