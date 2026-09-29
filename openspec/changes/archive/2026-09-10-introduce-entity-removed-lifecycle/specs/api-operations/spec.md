## ADDED Requirements

### Requirement: A removed Operation may be purged
An Operation whose `status` is `removed` MAY be permanently deleted via a `Purge` action, requiring the same Purge Grant (or global-admin status) required to purge a whole entity. Purge SHALL be blocked if any `ServiceOperationUsage` link still references the Operation, and SHALL be permitted, cascading their cleanup, if all remaining links reference the Operation through an already-removed path only. An `active` Operation SHALL NOT be purgeable directly — it must be removed first.

#### Scenario: A removed operation with no dependents is purged
- **WHEN** a Purge Grant holder invokes Purge on a `removed` Operation with no `ServiceOperationUsage` links
- **THEN** the Operation's row is permanently deleted

#### Scenario: Purge is rejected on an active operation
- **WHEN** Purge is invoked on an Operation whose status is `active`
- **THEN** the request is rejected — the Operation must be removed first

#### Scenario: Purge is blocked by an existing dependent link
- **WHEN** Purge is invoked on a `removed` Operation that still has a `ServiceOperationUsage` link
- **THEN** the request is rejected, naming the Service(s) still linked to it

### Requirement: AsyncAPI Operations support a manual deprecated override
An `Operation` SHALL carry a manual `deprecated` boolean field, defaulting to `false`, settable administratively (Django admin, fixtures/seed data) independent of any source document — since AsyncAPI, unlike OpenAPI, has no native keyword for expressing deprecation, and Operation deprecation warnings must be able to propagate to consumers the same way an OpenAPI-backed Endpoint's `deprecated` flag already does.

#### Scenario: An operation is manually flagged deprecated
- **WHEN** an administrator sets `deprecated=true` on an Operation through Django admin
- **THEN** the Operation's detail page shows a visible deprecation indicator, the same as a `deprecated` Endpoint's

#### Scenario: Deprecated override is independent of the source AsyncAPI document
- **WHEN** an `asyncapi`-typed API's spec is re-resolved and the Operation's underlying channel is unchanged
- **THEN** the manually-set `deprecated` flag is not reset or overwritten by the re-import
