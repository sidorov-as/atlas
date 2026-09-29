## MODIFIED Requirements

### Requirement: Operation documentation is entered administratively in this change
Creating or editing an `Operation`'s documentation SHALL NOT be available through any self-service, permission-gated API or UI; operation data is entered through Django admin, fixtures/seed data, or — for an `asyncapi`-typed API — the AsyncAPI importer (`asyncapi-operation-import` capability), which writes `ApiOperation` rows as a system-triggered side effect of that API's spec resolving, not as a client-facing create/edit operation.

#### Scenario: No create/edit endpoint exists
- **WHEN** a client requests to create or update an `Operation` through the catalog API
- **THEN** no such operation is exposed — only reading (list, detail) is available

#### Scenario: Importer writes are not a self-service operation
- **WHEN** an `asyncapi`-typed API's spec resolves and its parsed channel operations differ from its existing `ApiOperation` rows
- **THEN** the resulting `ApiOperation` creates/updates happen without any client request having asked to create or edit an `Operation`, and no create/edit operation is exposed through the catalog API as a result

### Requirement: Removing an operation is soft, preserving existing dependency links
Removing an `Operation` SHALL set its status to `removed` rather than deleting its row, and SHALL NOT delete any `ServiceOperationUsage` rows that reference it, regardless of whether the removal was triggered by an administrator or by the AsyncAPI importer noticing the operation is no longer in a re-parsed spec. A `removed` Operation SHALL remain visible in a dedicated section separate from an API's default (active) operation list, and any view of its existing Service links SHALL show a visible warning that the operation has been removed. A `removed` Operation whose operation reappears in a later re-parsed spec SHALL become `active` again without losing its existing `ServiceOperationUsage` links.

#### Scenario: Removing an operation preserves its links
- **WHEN** an Operation with existing `ServiceOperationUsage` links is removed
- **THEN** its status becomes `removed`, its row and all of its existing links remain in the database, and no `ServiceOperationUsage` row referencing it is deleted

#### Scenario: Removed operation is still reachable
- **WHEN** an API has one or more `removed` Operations
- **THEN** those Operations are visible in a "Removed operations" section, distinct from the default active-operation list

#### Scenario: A removed operation cannot receive new links
- **WHEN** a user views a `removed` Operation's page
- **THEN** no Link Service action is offered

#### Scenario: Removal is recorded in the admin audit log
- **WHEN** an Operation is marked `removed` through the Django admin action
- **THEN** the standard admin change log records who performed the action and when, independent of any product-facing notification (none is built in this change)

#### Scenario: An operation disappearing from a re-parsed spec is removed the same way
- **WHEN** an `asyncapi`-typed API's spec is re-resolved and no longer contains a channel operation matching a previously `active` Operation's `operation_key`
- **THEN** that Operation's status becomes `removed`, its row is not deleted, and its existing `ServiceOperationUsage` rows are preserved

#### Scenario: A removed operation revives when the spec adds it back
- **WHEN** an `asyncapi`-typed API's spec is re-resolved and now contains a channel operation matching a previously `removed` Operation's `operation_key`
- **THEN** that Operation's status becomes `active`, its documentation fields are updated from the reappeared operation, and its existing `ServiceOperationUsage` links are unchanged
