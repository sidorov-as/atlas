## ADDED Requirements

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
