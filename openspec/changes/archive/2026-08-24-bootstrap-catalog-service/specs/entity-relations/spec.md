## ADDED Requirements

### Requirement: Relations are derived, not authored
Typed relations SHALL be computed from `spec` reference fields, not accepted as direct input, and materialized in both directions.

#### Scenario: dependsOn produces a reverse dependencyOf
- **WHEN** Component *A* has `dependsOn: [resource:B]` in its spec
- **THEN** `GET /api/resources/B/relations/` lists `dependencyOf: component:A`

#### Scenario: Direct relation authoring is rejected
- **WHEN** a request attempts to set a relation directly rather than through a `spec` reference field
- **THEN** the request is rejected, since relations have no independent write path

#### Scenario: memberOf/hasMember is a single relationship, not two declarations
- **WHEN** a User is added to a Group's membership (via Django admin, from either the Group or the User side)
- **THEN** `GET /api/groups/{id}/relations/` lists `hasMember` for that User and `GET /api/users/{id}/relations/` lists `memberOf` for that Group, and there is no way for the two to disagree since both are read from the same underlying relationship

#### Scenario: system produces a reverse partOf/hasPart
- **WHEN** a Component, Resource, or API has `spec.system: system:user-management`
- **THEN** `GET /api/{kind}/{id}/relations/` for that entity lists `partOf: system:user-management`, and `GET /api/systems/{id}/relations/` for that System lists `hasPart` for every Component, Resource, and API whose `system` field points at it

#### Scenario: providesApis produces a reverse apiProvidedBy
- **WHEN** a Component has `providesApis: [api:user-api]` in its spec
- **THEN** `GET /api/apis/user-api/relations/` lists `apiProvidedBy: component:{name}` for that Component

#### Scenario: consumesApis produces a reverse apiConsumedBy
- **WHEN** a Component has `consumesApis: [api:user-api]` in its spec
- **THEN** `GET /api/apis/user-api/relations/` lists `apiConsumedBy: component:{name}` for that Component

#### Scenario: One API is both provided and consumed by different Components
- **WHEN** Component *A* has `providesApis: [api:X]` and Component *B* (different from *A*) has `consumesApis: [api:X]`
- **THEN** `GET /api/apis/X/relations/` lists both `apiProvidedBy: component:A` and `apiConsumedBy: component:B`, without either relation overwriting the other

### Requirement: Targeted recomputation on write
A write to an entity SHALL recompute only that entity's outgoing derived edges, not rebuild the full relations table.

#### Scenario: Editing dependsOn updates only the edited entity's edges
- **WHEN** a Component's `dependsOn` list is changed via PATCH
- **THEN** only that Component's outgoing `dependsOn` relation rows are replaced; other entities' relation rows are untouched

### Requirement: Relations endpoint lists both directions
`GET /api/{kind}/{id}/relations/` SHALL return every relation where the entity is either the subject or the object, labeled with the correct forward or reverse predicate.

#### Scenario: Owner relation appears on both sides
- **WHEN** a System has `spec.owner: group:identity-team`
- **THEN** `GET /api/systems/{id}/relations/` lists `ownedBy: group:identity-team` and `GET /api/groups/{id}/relations/` for that Group lists `ownerOf: system:{name}`
