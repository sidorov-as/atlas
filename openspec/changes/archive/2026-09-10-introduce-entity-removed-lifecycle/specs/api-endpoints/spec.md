## ADDED Requirements

### Requirement: A removed Endpoint may be purged
An Endpoint whose `status` is `removed` MAY be permanently deleted via a `Purge` action, requiring the same Purge Grant (or global-admin status) required to purge a whole entity. Purge SHALL be blocked if any active `ServiceEndpointUsage` link still references the Endpoint, and SHALL be permitted, cascading their cleanup, if all remaining `ServiceEndpointUsage` links reference the Endpoint through an already-removed path only. An `active` Endpoint SHALL NOT be purgeable directly — it must be removed first.

#### Scenario: A removed endpoint with no dependents is purged
- **WHEN** a Purge Grant holder invokes Purge on a `removed` Endpoint with no `ServiceEndpointUsage` links
- **THEN** the Endpoint's row is permanently deleted

#### Scenario: Purge is rejected on an active endpoint
- **WHEN** Purge is invoked on an Endpoint whose status is `active`
- **THEN** the request is rejected — the Endpoint must be removed first

#### Scenario: Purge is blocked by an existing dependent link
- **WHEN** Purge is invoked on a `removed` Endpoint that still has a `ServiceEndpointUsage` link
- **THEN** the request is rejected, naming the Service(s) still linked to it
