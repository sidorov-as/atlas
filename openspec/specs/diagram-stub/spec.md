# diagram-stub Specification

## Purpose
Generated C4 diagram endpoint that validates supported target/view pairs and returns local PlantUML-backed images.

## Requirements

### Requirement: Generated diagram for a valid target
`GET /api/diagrams/system/{id}/?view=context` and `GET /api/diagrams/component/{id}/?view=component` SHALL return generated C4 SVG content for valid target/view combinations. The endpoint SHALL no longer return static placeholder content.

#### Scenario: Valid System Context returns generated SVG
- **WHEN** a valid System id is requested with `view=context`
- **THEN** the endpoint returns 200 with generated `image/svg+xml` content

#### Scenario: Valid Component Diagram returns generated SVG
- **WHEN** a valid Component id is requested with `view=component`
- **THEN** the endpoint returns 200 with generated `image/svg+xml` content

### Requirement: Validation of diagram targets
An invalid `id` or `view` SHALL return an error status rather than a partial or malformed SVG.

#### Scenario: Unknown entity id
- **WHEN** the endpoint is called with an `id` that doesn't exist for the requested kind
- **THEN** it returns 404

#### Scenario: Invalid view parameter
- **WHEN** the endpoint is called with a `view` value outside the valid view for the requested kind
- **THEN** it returns 400

#### Scenario: Valid view for an unsupported kind
- **WHEN** the endpoint is called for a Resource, API, Group, or User with any view
- **THEN** it returns 400
