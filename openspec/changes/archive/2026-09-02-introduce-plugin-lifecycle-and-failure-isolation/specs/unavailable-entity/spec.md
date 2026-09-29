## ADDED Requirements

### Requirement: An entity with no active kind provider becomes Unavailable
When a Catalog Entity's kind has no currently registered handler, the Entity Service SHALL represent it as a read-only Unavailable Entity rather than erroring.

#### Scenario: Reading an entity of a removed kind
- **WHEN** an entity's kind provider is not currently registered and the entity is retrieved
- **THEN** the response includes the entity's identity and common metadata, marked unavailable, without kind-specific `spec` data

### Requirement: Identity and relationships remain intact
An Unavailable Entity's identity and relations to other entities SHALL remain queryable and unchanged.

#### Scenario: Relations to an unavailable entity still resolve
- **WHEN** another entity has a relation pointing at an Unavailable Entity
- **THEN** that relation still resolves, identifying the Unavailable Entity by its stable id and common metadata

### Requirement: Unavailable Entities reject writes
A write (create, update, delete) targeting an Unavailable Entity's kind-specific data SHALL be rejected, since no handler exists to process it.

#### Scenario: Editing an unavailable entity's kind-specific data is rejected
- **WHEN** a client attempts to update the kind-specific `spec` of an Unavailable Entity
- **THEN** the request is rejected, identifying the kind as unavailable

### Requirement: Restoring the kind provider restores full access
When a kind's handler becomes registered again, its previously Unavailable Entities SHALL become fully available, including kind-specific data preserved from before.

#### Scenario: Reinstalling the kind provider restores an entity
- **WHEN** a kind's provider plugin is reselected and its handler registers again
- **THEN** entities of that kind are no longer Unavailable and their preserved kind-specific data is available again
