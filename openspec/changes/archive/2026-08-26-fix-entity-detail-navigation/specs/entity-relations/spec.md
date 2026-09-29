## MODIFIED Requirements

### Requirement: Relations endpoint lists both directions
`GET /api/{kind}/{id}/relations/` SHALL return every relation where the entity is either the subject or the object, labeled with the correct forward or reverse predicate. Each entry SHALL identify the target entity's kind and id (`targetKind`, `targetId`), in addition to its `target` ref string.

#### Scenario: Owner relation appears on both sides
- **WHEN** a System has `spec.owner: group:identity-team`
- **THEN** `GET /api/systems/{id}/relations/` lists `ownedBy: group:identity-team` and `GET /api/groups/{id}/relations/` for that Group lists `ownerOf: system:{name}`

#### Scenario: Relation entry identifies its target entity
- **WHEN** a relation is returned by `GET /api/{kind}/{id}/relations/`
- **THEN** that entry includes `targetKind` and `targetId` identifying the target entity, alongside its existing `target` ref string
