## MODIFIED Requirements

### Requirement: First-claim arbitration
When an ingestion run encounters a ref, the system SHALL arbitrate against any existing entity's source rather than silently overwriting it. Arbitration SHALL happen before an `EntityIntent` is submitted to the core Entity Service; a rejected claim SHALL NOT reach the Entity Service at all.

#### Scenario: YAML claims an unclaimed ref
- **WHEN** ingestion encounters a ref with no existing entity
- **THEN** a new entity is created with `source_kind=yaml` and the claiming repository set

#### Scenario: YAML collides with a manual entity
- **WHEN** ingestion encounters a ref already claimed by a manual entity
- **THEN** the ingestion claim is rejected before any `EntityIntent` is submitted, a conflict is recorded, and the manual entity's fields are unchanged

#### Scenario: Same repo re-claims its own entity
- **WHEN** ingestion encounters a ref already claimed by the same `RegisteredRepository`
- **THEN** the entity's fields are overwritten in full from the manifest, via an `EntityIntent` submitted to the Entity Service

#### Scenario: A different repo collides with an existing YAML claim
- **WHEN** ingestion encounters a ref already claimed by a different `RegisteredRepository`
- **THEN** the ingestion claim is rejected before any `EntityIntent` is submitted, a conflict is recorded, and the existing entity's fields are unchanged
