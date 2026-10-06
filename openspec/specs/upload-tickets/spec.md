## Purpose

Upload tickets are one-time, expiring links that let a caller with write permission send a raw file body directly to Atlas for one field of one entity, without routing the content through an LLM and without exposing a Personal Access Token. Plugins register the fields they accept (upload targets) with an adapter that validates and applies the body.

## Requirements

### Requirement: A caller with write permission can request an upload ticket for one target
Atlas SHALL let an authenticated caller request an upload ticket for a single `(entity, field)` target. The request SHALL be authorized exactly as a regular write to that field would be: the caller's PAT scopes and the owning user's RBAC SHALL both permit it, and a YAML-managed entity SHALL be rejected. The result SHALL contain the upload path, the expiry time, and the maximum body size. Ticket parameters required by the target (for example a SQL dialect) SHALL be supplied and validated at request time.

#### Scenario: Ticket issued for a writable target
- **WHEN** a caller with write permission requests a ticket for the `spec` field of an API
- **THEN** a ticket is issued with an upload path, an expiry, and a maximum size

#### Scenario: Caller without write permission
- **WHEN** a caller whose scopes or RBAC do not permit writing the target requests a ticket
- **THEN** the request is rejected and no ticket is created

#### Scenario: YAML-managed entity
- **WHEN** a caller requests a ticket for an entity managed by catalog-info.yaml
- **THEN** the request is rejected as read-only

#### Scenario: Unknown target
- **WHEN** a caller requests a ticket for a field that no plugin has registered as an upload target for that entity's kind
- **THEN** the request is rejected with an error naming the supported fields

#### Scenario: Invalid ticket parameters
- **WHEN** a caller requests a schema ticket with an unsupported dialect
- **THEN** the request is rejected and no ticket is created

### Requirement: Upload tickets are unguessable, hashed at rest, and bound to their issuer
The ticket token SHALL be generated from a cryptographically secure source with at least 256 bits of entropy. Atlas SHALL store only a hash of the token, never the token itself. A ticket SHALL record the target entity, the field, the target parameters, the issuing user, the issuing Personal Access Token, the expiry time, and the size limit. The full URL or token SHALL NOT be written to application or access logs.

#### Scenario: Token is not recoverable from storage
- **WHEN** a ticket has been issued and the database is inspected
- **THEN** the stored value is a hash and the token cannot be derived from it

#### Scenario: Token is returned once
- **WHEN** a ticket is issued
- **THEN** the token appears only in that response and no later read returns it

#### Scenario: Token absent from logs
- **WHEN** a ticket is issued and used
- **THEN** no log line produced by Atlas contains the token

### Requirement: The upload endpoint accepts the raw body without separate authentication
Atlas SHALL expose a `PUT` endpoint addressed by the ticket token. It SHALL NOT require an `Authorization` header or a session. The request body SHALL be the raw file content. The endpoint SHALL apply the body to the ticket's target through the target's adapter, on behalf of the issuing user, using the same write permission checks as a regular write.

#### Scenario: Successful upload
- **WHEN** a client sends `PUT` with the raw spec to a valid, unexpired, unused ticket URL
- **THEN** the spec is applied to the API and the response reports success

#### Scenario: Unknown token
- **WHEN** a client sends `PUT` to a URL whose token matches no ticket
- **THEN** the response is `404` and nothing is written

#### Scenario: Permission lost after issuance
- **WHEN** the issuing user no longer has write permission on the target when the `PUT` arrives
- **THEN** the write is rejected and the ticket stays unused until it expires

#### Scenario: Body exceeds the size limit
- **WHEN** the request body is larger than the ticket's size limit
- **THEN** the response is `413` and nothing is written

### Requirement: A ticket is valid until a successful upload or expiry
A ticket SHALL expire after a configured time to live. A ticket SHALL be consumed only by an upload the target accepted. A failed upload (validation error, transport failure, permission failure) SHALL leave the ticket usable until it expires, so the client can retry. An expired or consumed ticket SHALL be rejected.

#### Scenario: Retry after a failed upload
- **WHEN** an upload is rejected because the body failed validation, and the client sends a corrected body to the same URL before expiry
- **THEN** the corrected body is accepted

#### Scenario: Second upload after success
- **WHEN** a client sends `PUT` to a ticket that already accepted an upload
- **THEN** the response is `404` and nothing is written

#### Scenario: Expired ticket
- **WHEN** a client sends `PUT` after the ticket's expiry
- **THEN** the response is `404` and nothing is written

#### Scenario: Concurrent uploads
- **WHEN** two valid uploads for the same ticket arrive at the same time
- **THEN** at most one is accepted

### Requirement: Upload responses share one shape, and failures carry the reason
A successful upload SHALL return `{ok, summary}`, where `ok` means the content was accepted and stored and `summary` is an object filled by the target's adapter. A rejected upload SHALL return an error response whose body states the reason, including the parser or validator message where one exists.

#### Scenario: Summary comes from the adapter
- **WHEN** an upload succeeds
- **THEN** the response contains `ok` true and the adapter's summary object

#### Scenario: Rejection reason is returned
- **WHEN** an upload is rejected because the content is not a parseable document
- **THEN** the error response includes the validator's message

### Requirement: Plugins register upload targets with an adapter
Atlas SHALL provide an extension point through which a plugin registers an upload target keyed by `(kind, field)`, together with an adapter that receives the entity, the raw body, and the ticket parameters and returns a summary. Registering a target SHALL NOT require changes to the ticket core. A target registered by a plugin that is not installed SHALL NOT exist.

#### Scenario: Target available only with its plugin
- **WHEN** a distribution does not select the plugin that registers a target
- **THEN** a ticket request for that target is rejected as unknown

#### Scenario: Adapter failure leaves no partial write
- **WHEN** an adapter raises a validation error
- **THEN** the target's stored content is unchanged

### Requirement: Unused tickets stop working when their issuing PAT stops working
A ticket SHALL be rejected if the Personal Access Token that issued it has been revoked or has expired, or if the owning account is inactive.

#### Scenario: PAT revoked before upload
- **WHEN** a PAT issues a ticket, is then revoked, and the client sends `PUT`
- **THEN** the response is `404` and nothing is written

### Requirement: Stale tickets are cleaned up
Atlas SHALL delete expired and consumed tickets after a retention period, so the ticket table does not grow without bound.

#### Scenario: Old tickets removed
- **WHEN** the cleanup runs and a ticket expired longer ago than the retention period
- **THEN** the ticket is deleted
