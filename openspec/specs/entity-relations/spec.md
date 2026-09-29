# entity-relations Specification

## Purpose
Derivation and storage of typed, bidirectional relations from entity `spec` reference fields, targeted recomputation on write, and the `GET /api/{kind}/{id}/relations/` endpoint.

## Requirements

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
`GET /api/{kind}/{id}/relations/` SHALL return every relation where the entity is either the subject or the object, labeled with the correct forward or reverse predicate. Each entry SHALL identify the target entity's kind and id (`targetKind`, `targetId`), in addition to its `target` ref string.

#### Scenario: Owner relation appears on both sides
- **WHEN** a System has `spec.owner: group:identity-team`
- **THEN** `GET /api/systems/{id}/relations/` lists `ownedBy: group:identity-team` and `GET /api/groups/{id}/relations/` for that Group lists `ownerOf: system:{name}`

#### Scenario: Relation entry identifies its target entity
- **WHEN** a relation is returned by `GET /api/{kind}/{id}/relations/`
- **THEN** that entry includes `targetKind` and `targetId` identifying the target entity, alongside its existing `target` ref string

### Requirement: Relation entries surface a removed or deprecated target's status
`GET /api/{kind}/{id}/relations/` SHALL include the target entity's current `status` (`active`/`removed`) and `deprecated` flag alongside each relation entry's existing `target`/`targetKind`/`targetId` fields, so a client rendering a relation (e.g. a System's `hasPart` list, a Component's `dependsOn`) can warn when the target is no longer active or is going away.

#### Scenario: A relation to a removed target reports its status
- **WHEN** `GET /api/systems/{id}/relations/` is called for a System whose `hasPart` includes a now-`removed` Component
- **THEN** that relation entry includes `status: "removed"` for the target

#### Scenario: A relation to a deprecated target reports its flag
- **WHEN** `GET /api/components/{id}/relations/` is called for a Component whose `dependsOn` includes a `deprecated` Resource
- **THEN** that relation entry includes `deprecated: true` for the target

#### Scenario: A relation to an active, non-deprecated target reports plainly
- **WHEN** a relation's target is `active` and not `deprecated`
- **THEN** the relation entry reports that status without any warning-worthy flag set
