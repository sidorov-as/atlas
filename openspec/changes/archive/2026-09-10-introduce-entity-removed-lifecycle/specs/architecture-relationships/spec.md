## ADDED Requirements

### Requirement: Architecture Relationship listings surface a removed or deprecated endpoint's status
An Architecture Relationship listing entry SHALL include the source and target entities' current `status` (`active`/`removed`) and `deprecated` flag, so a Relations tab or C4 diagram consumer can visibly warn when a declared interaction points at an entity that is no longer active or is going away, rather than presenting it as a healthy edge.

#### Scenario: A relationship to a removed target is listed with its status
- **WHEN** a Component's Architecture Relationship listing includes an interaction whose target is now `removed`
- **THEN** that listing entry includes `status: "removed"` for the target

#### Scenario: A relationship from a removed source is listed with its status
- **WHEN** a `removed` Component's outgoing Architecture Relationship is listed from its target's perspective
- **THEN** that listing entry includes `status: "removed"` for the source

#### Scenario: A relationship to a deprecated target is listed with its flag
- **WHEN** a Component's Architecture Relationship listing includes an interaction whose target is `deprecated`
- **THEN** that listing entry includes `deprecated: true` for the target
