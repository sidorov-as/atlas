## ADDED Requirements

### Requirement: Spec resolution triggers operation sync
Whenever an `ApiDetails` record is saved with `type='asyncapi'` and a non-empty `spec_content`, the system SHALL parse `spec_content` and synchronize that API's `ApiOperation` rows to match it, regardless of which write path produced the save (create, patch, or the ingestor's periodic `spec_url` refresh).

#### Scenario: Sync runs after creating an API with an inline AsyncAPI spec
- **WHEN** a user creates an `asyncapi`-typed API with `spec_source='inline'` and a valid AsyncAPI document as `spec_content`
- **THEN** `ApiOperation` rows are created for every channel operation in that document before the create request completes

#### Scenario: Sync runs after the periodic refresh of a URL-sourced spec
- **WHEN** the ingestor's periodic refresh re-fetches a `spec_url` and the response is a valid, changed AsyncAPI document
- **THEN** that API's `ApiOperation` rows are synchronized to the newly-fetched document within the same refresh pass, without any code outside `atlas_plugin_apis` invoking the sync explicitly

#### Scenario: Non-asyncapi-typed APIs are never synced
- **WHEN** an API's `type` is `openapi`, `grpc`, or `graphql`
- **THEN** no operation sync is attempted and its `ApiOperation` rows (if any, e.g. from prior manual authoring) are left untouched

#### Scenario: Empty spec content is not synced
- **WHEN** an `asyncapi`-typed API's `spec_content` is empty (`spec_source='none'`, or a URL/inline source that resolved to nothing)
- **THEN** no operation sync is attempted and existing `ApiOperation` rows are left untouched

### Requirement: Operation lifecycle is derived from diffing the parsed spec against existing operations
For an `asyncapi`-typed API, the system SHALL reconcile parsed channel operations against existing `ApiOperation` rows keyed by `operation_key`: creating rows for new operations, updating fields in place for changed operations (preserving `id` and any `ServiceOperationUsage` links), reviving a `removed` row whose operation reappears, and setting `status='removed'` on an `active` row whose operation disappears. No `ApiOperation` row is ever deleted by this process, and no `ServiceOperationUsage` row is ever deleted or modified by it.

#### Scenario: A new operation creates an ApiOperation row
- **WHEN** a re-parsed spec contains an `operation_key` with no existing `ApiOperation` on that API
- **THEN** a new `ApiOperation` is created with `status='active'` and the parsed documentation fields

#### Scenario: A changed operation updates the existing row without changing its identity
- **WHEN** a re-parsed spec's operation for an existing `active` `ApiOperation` has a different `channel_protocol`, `operation_id`, `summary`, `description`, `tags`, or `message` set than what's stored
- **THEN** the existing `ApiOperation` row is updated in place; its `id` is unchanged and any `ServiceOperationUsage` rows referencing it remain valid

#### Scenario: An operation missing from the new spec is soft-removed
- **WHEN** a re-parsed spec no longer contains an `operation_key` that a previously `active` `ApiOperation` on that API has
- **THEN** that `ApiOperation`'s `status` becomes `removed`, the row is not deleted, and any `ServiceOperationUsage` rows referencing it are not deleted

#### Scenario: A previously removed operation that reappears is revived
- **WHEN** a re-parsed spec now contains an `operation_key` matching a `removed` `ApiOperation` on that API
- **THEN** that `ApiOperation`'s `status` becomes `active` again, its documentation fields are updated from the reappeared operation, and its `id` and any existing `ServiceOperationUsage` rows are unchanged

### Requirement: Both AsyncAPI 2.x and 3.0 are parsed into one operation shape, with direction normalized
The parser SHALL accept both an `asyncapi: "2.x"` document and an `asyncapi: "3.x"` document and normalize each into the same `ApiOperation` shape. `direction` SHALL be computed from the document's own version-specific vocabulary, never stored as the raw `publish`/`subscribe` words, per the mapping already codified in the `api-operations` capability: 2.x `publish` → `receive`; 2.x `subscribe` → `send`; 3.0 `action: send`/`action: receive` pass through unchanged.

#### Scenario: A 2.x publish operation is imported as receive
- **WHEN** a 2.x document's channel has a `publish` field
- **THEN** the resulting `ApiOperation.direction` is `receive`

#### Scenario: A 2.x subscribe operation is imported as send
- **WHEN** a 2.x document's channel has a `subscribe` field
- **THEN** the resulting `ApiOperation.direction` is `send`

#### Scenario: A 3.0 operation's action maps through unchanged
- **WHEN** a 3.0 document's `operations` entry has `action: send` or `action: receive`
- **THEN** the resulting `ApiOperation.direction` matches that `action` value exactly

#### Scenario: operation_key uses the 3.0 operations-map key
- **WHEN** a 3.0 document's `operations` map has an entry under key `onBookingConfirmed`
- **THEN** the resulting `ApiOperation.operation_key` is `onBookingConfirmed`

#### Scenario: operation_key falls back to channel plus direction for 2.x
- **WHEN** a 2.x document's channel `booking.confirmed` has a `subscribe` field
- **THEN** the resulting `ApiOperation.operation_key` is derived from `booking.confirmed` and `send` (its mapped direction), unique within that API

### Requirement: Channel protocol is resolved only when unambiguous
The parser SHALL populate `channel_protocol` only when the document unambiguously identifies one server for the channel's operation (a 2.x document declaring exactly one top-level server, or a 3.0 channel referencing exactly one server); otherwise `channel_protocol` SHALL be left empty rather than guessed.

#### Scenario: Single top-level server resolves protocol for a 2.x channel
- **WHEN** a 2.x document declares exactly one entry in its top-level `servers` map with `protocol: kafka`
- **THEN** every parsed operation's `channel_protocol` is `kafka`

#### Scenario: Multiple servers leave protocol unresolved for a 2.x channel
- **WHEN** a 2.x document declares more than one entry in its top-level `servers` map
- **THEN** parsed operations' `channel_protocol` is left empty rather than guessing among the candidates

#### Scenario: A 3.0 channel referencing exactly one server resolves protocol
- **WHEN** a 3.0 document's channel references exactly one entry in the top-level `servers` map
- **THEN** that channel's parsed operations' `channel_protocol` matches that server's `protocol`

### Requirement: Message payload schema is stored unresolved
A message's payload schema that is (or contains) a `$ref` SHALL be stored with that `$ref` string verbatim; the parser SHALL NOT resolve it against `components`/referenced message definitions.

#### Scenario: A message payload that is a $ref is stored as-is
- **WHEN** an operation's message payload is `{"$ref": "#/components/schemas/BookingConfirmed"}`
- **THEN** the resulting `ApiOperation` message's schema has that `$ref` string and no expanded `properties`

#### Scenario: An operation referencing only a $ref'd message yields a name-only entry
- **WHEN** a 3.0 operation's `messages` entry is a bare `$ref` into a channel's message map with no inline payload resolvable by this parser
- **THEN** the resulting message entry has a name derived from the `$ref`'s last path segment and no schema or example

### Requirement: A channel operation with multiple message alternatives produces multiple message entries
An operation whose message is declared as more than one alternative shape (e.g. a 2.x `oneOf` message) SHALL produce one `ApiOperation.message` entry per alternative.

#### Scenario: A oneOf message produces multiple entries
- **WHEN** a channel operation's `message` is a `oneOf` list of two message objects
- **THEN** the resulting `ApiOperation.message` has two entries, one per alternative

### Requirement: Parse failures never interrupt the save/refresh path and are recorded, not silent
A spec that fails to parse as recognizable AsyncAPI SHALL NOT raise an exception out of the create, patch, or periodic-refresh path, and SHALL NOT modify any existing `ApiOperation` row for that API. A single channel operation within an otherwise-parseable spec that fails to map to the operation shape SHALL be skipped without failing the rest of the spec's import. Every successful sync SHALL update `ApiDetails.operations_synced_at` and clear `ApiDetails.operations_sync_failed`; every spec-level failure SHALL set `ApiDetails.operations_sync_failed` without changing `operations_synced_at`.

#### Scenario: An unparseable spec leaves existing operations untouched
- **WHEN** an `asyncapi`-typed API's `spec_content` has no recognizable `asyncapi` version key or no usable `channels`
- **THEN** the save or refresh completes successfully, existing `ApiOperation` rows for that API are unchanged, and `ApiDetails.operations_sync_failed` becomes `true`

#### Scenario: One malformed channel operation doesn't block the rest of the spec
- **WHEN** a spec has several valid channel operations and one whose shape the parser can't map
- **THEN** the valid operations are synced normally and the malformed one is skipped and logged, without setting `operations_sync_failed`

#### Scenario: A successful sync clears a prior failure
- **WHEN** an API previously had `operations_sync_failed=true` and its spec is re-resolved into a document that now parses successfully
- **THEN** `operations_sync_failed` becomes `false` and `operations_synced_at` is updated to the current time
