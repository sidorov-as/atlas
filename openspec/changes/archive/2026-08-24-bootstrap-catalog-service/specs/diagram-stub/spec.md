## ADDED Requirements

### Requirement: Placeholder diagram for a valid target
`GET /api/diagrams/{kind}/{id}/?view={context|container|component}` SHALL return a 200 with `image/svg+xml` content for any valid `(kind, id, view)` combination.

#### Scenario: Valid target returns a placeholder SVG
- **WHEN** a valid `(kind, id)` pair and a `view` in `{context, container, component}` are requested
- **THEN** the endpoint returns 200 with `image/svg+xml` content, even though it is placeholder content in v1

### Requirement: Validation of diagram targets
An invalid `id` or `view` SHALL return an error status rather than a partial or malformed SVG.

#### Scenario: Unknown entity id
- **WHEN** the endpoint is called with an `id` that doesn't exist for the given `kind`
- **THEN** it returns 404

#### Scenario: Invalid view parameter
- **WHEN** the endpoint is called with a `view` value outside `{context, container, component}`
- **THEN** it returns 400
