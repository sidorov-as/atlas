## ADDED Requirements

### Requirement: Single transaction owns entity lifecycle changes
Every create, update, or delete of a `CatalogEntity` SHALL run inside one transaction owned by the Entity Service: authorize, validate common metadata, resolve the kind handler, change `CatalogEntity`, invoke the kind handler, write an audit record, then commit.

#### Scenario: A kind handler failure rolls back the whole change
- **WHEN** the kind handler's `create_details` raises during entity creation
- **THEN** no `CatalogEntity` row, kind-details row, or audit record persists from that attempt

#### Scenario: Successful create writes entity, details, and audit atomically
- **WHEN** an entity is created successfully
- **THEN** its `CatalogEntity` row, its kind-details row, and one audit record for the creation all commit together

### Requirement: Common metadata validation is kind-independent
The Entity Service SHALL validate common envelope fields (name, title, description, labels, tags, links) itself, before invoking any kind handler, so no kind handler needs to reimplement envelope validation.

#### Scenario: Invalid common metadata never reaches the kind handler
- **WHEN** a create request has an invalid `name` (e.g. containing an unsupported character)
- **THEN** the request is rejected before the kind handler's `create_details` is invoked

### Requirement: No lifecycle path bypasses the Entity Service
Manual UI/API entity creation, update, and deletion SHALL go exclusively through the Entity Service; no other code path SHALL create, update, or delete a `CatalogEntity` row directly.

#### Scenario: REST create request is served by the Entity Service
- **WHEN** a client calls the create endpoint for a registered kind
- **THEN** the resulting `CatalogEntity` and audit record were produced by the Entity Service's transaction, not by a viewset calling the ORM directly

### Requirement: Deletion validity is checked inside the delete transaction
`validate_delete` SHALL run inside the same transaction as the delete, not as a separate pre-check, so a delete cannot succeed against state that changed between check and commit.

#### Scenario: A dependent added mid-request blocks the delete
- **WHEN** a delete request's `validate_delete` check and the delete itself run in the same transaction
- **THEN** any dependency created concurrently and visible at commit time still blocks the delete
