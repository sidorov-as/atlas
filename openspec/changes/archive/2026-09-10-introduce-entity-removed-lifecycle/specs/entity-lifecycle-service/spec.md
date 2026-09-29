## MODIFIED Requirements

### Requirement: Single transaction owns entity lifecycle changes
Every create, update, delete, remove, revive, or purge of a `CatalogEntity` SHALL run inside one transaction owned by the Entity Service: authorize, validate common metadata, resolve the kind handler, change `CatalogEntity`, invoke the kind handler, write an audit record, then commit.

#### Scenario: A kind handler failure rolls back the whole change
- **WHEN** the kind handler's `create_details` raises during entity creation
- **THEN** no `CatalogEntity` row, kind-details row, or audit record persists from that attempt

#### Scenario: Successful create writes entity, details, and audit atomically
- **WHEN** an entity is created successfully
- **THEN** its `CatalogEntity` row, its kind-details row, and one audit record for the creation all commit together

#### Scenario: Remove, revive, and purge each write their own audit record atomically
- **WHEN** an entity is removed, revived, or purged
- **THEN** the resulting status change (or, for purge, row deletion) and its audit record commit together in one transaction, with no partial state possible if the transaction fails

### Requirement: No lifecycle path bypasses the Entity Service
Manual UI/API entity creation, update, deletion, removal, revival, and purge SHALL go exclusively through the Entity Service; no other code path SHALL create, update, delete, remove, revive, or purge a `CatalogEntity` row directly.

#### Scenario: REST create request is served by the Entity Service
- **WHEN** a client calls the create endpoint for a registered kind
- **THEN** the resulting `CatalogEntity` and audit record were produced by the Entity Service's transaction, not by a viewset calling the ORM directly

#### Scenario: Remove/revive/purge requests are served by the Entity Service
- **WHEN** a client calls the remove, revive, or purge endpoint for an entity
- **THEN** the resulting status change (or deletion) and audit record were produced by the Entity Service's transaction, not by a viewset or ingestion job writing the status field directly

### Requirement: Deletion validity is checked inside the delete transaction
`validate_delete` SHALL run inside the same transaction as the delete, not as a separate pre-check, so a delete cannot succeed against state that changed between check and commit. The same rule SHALL apply to purge's reference-scanning validation.

#### Scenario: A dependent added mid-request blocks the delete
- **WHEN** a delete request's `validate_delete` check and the delete itself run in the same transaction
- **THEN** any dependency created concurrently and visible at commit time still blocks the delete

#### Scenario: A dependent added mid-request blocks a purge
- **WHEN** a purge request's reference-scanning check and the row deletion run in the same transaction
- **THEN** any active reference created concurrently and visible at commit time still blocks the purge
