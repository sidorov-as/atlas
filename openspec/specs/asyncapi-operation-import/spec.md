## Purpose

AsyncAPI Operation Import parses an `asyncapi`-typed API's resolved `spec_content` (AsyncAPI 2.x or 3.0) into `ApiOperation` rows, triggered on every successful spec resolution (create, patch, or the ingestor's periodic `spec_url` refresh). It owns the create/update/revive/soft-remove upsert rules against existing `ApiOperation` rows, the verified `publish`/`subscribe`/`action` → `direction` mapping, `channel_protocol` resolution, `$ref` resolution for message identity and payload/headers schemas against the document's own components, and parse-failure handling — so that pointing Atlas at a live AsyncAPI document produces real Operations without a human hand-transcribing them.

## Requirements

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

### Requirement: Message identity and payload schema are resolved against the document's own components
When a channel's message reference — a channel's `messages.<name>` entry (whether reached via an operation's `messages[]` entry or, absent any `messages[]` narrowing, taken as one of "every message this channel defines"), or (for 2.x) a `publish`/`subscribe`/`oneOf` message field — is itself an unresolved `$ref` rather than the real Message Object, the parser SHALL dereference it against the same document (typically into `components.messages`), following as many further `$ref` hops as the document actually chains, to find the real message object before mapping it. Whether a node is "the real Message Object" or "still a reference" is determined structurally (does it carry a `$ref` key), not by whether it happens to have a `payload` — every Message Object field, including `payload`, is optional per AsyncAPI's own spec, so a message with only a `name`/`title`/`summary` and no `payload` is still the real object, not a reference waiting to be resolved further. A message's payload schema that is (or contains) a `$ref` SHALL be resolved against the document's `components.schemas`, recursively; sibling keys next to that `$ref` are discarded (not merged — AsyncAPI's Reference Object semantics, both 2.x and 3.0, treat sibling keys as meaningless). The only cases where a `$ref` is left unresolved (schema) or a message reference yields a name-only stub (identity) are: the pointer does not resolve to anything defined in the document, or resolving it would re-enter a `$ref` already being expanded along the same resolution path (a reference cycle) — this applies equally to a single hop and to a chain of several.

#### Scenario: A message payload that is a $ref is resolved
- **WHEN** an operation's message payload is `{"$ref": "#/components/schemas/BookingConfirmed"}` and `#/components/schemas/BookingConfirmed` is an inline object schema
- **THEN** the resulting `ApiOperation` message's schema has that schema's expanded `type`/`properties`/`required`, not the bare `$ref` string

#### Scenario: A channel's message-map entry that is itself a $ref is dereferenced
- **WHEN** a 3.0 channel's `messages.<name>` entry is `{"$ref": "#/components/messages/OrderCreated"}` and `#/components/messages/OrderCreated` is an inline message object with a `payload`
- **THEN** an operation referencing that channel message's resulting entry has the real message's `name`/`payload`/`summary`, not a name-only stub with no schema

#### Scenario: A 2.x bare-$ref message field is dereferenced
- **WHEN** a 2.x channel's `publish`/`subscribe`/`oneOf` `message` field is `{"$ref": "#/components/messages/X"}` and `#/components/messages/X` is an inline message object with a `payload`
- **THEN** the resulting message entry has that message's real `name`/`payload`, the same as the equivalent 3.0 case, instead of an entry with an empty `name` and no schema

#### Scenario: A genuinely unresolvable message reference still yields a name-only entry
- **WHEN** a message reference's `$ref` points at something not defined anywhere in the document
- **THEN** the resulting message entry falls back to a name derived from the `$ref`'s last path segment, with no schema or example, exactly as today

#### Scenario: A multi-hop message reference chain is fully dereferenced
- **WHEN** a channel's `messages.<name>` entry is `{"$ref": "#/components/messages/A"}`, `#/components/messages/A` is itself `{"$ref": "#/components/messages/B"}`, and `#/components/messages/B` is an inline message object with a `payload`
- **THEN** the resulting message entry has `B`'s real `name`/`payload`, following both hops, not just the first

#### Scenario: A message-identity reference cycle stops without looping
- **WHEN** a channel's `messages.<name>` entry is `{"$ref": "#/components/messages/A"}` and `#/components/messages/A` is `{"$ref": "#/components/messages/B"}` whose own value is `{"$ref": "#/components/messages/A"}` (a cycle between `A` and `B`, neither ever inline)
- **THEN** dereferencing stops at the point the cycle is detected and falls back to a name-only entry, the same shape as a dangling reference, without looping or raising

#### Scenario: A channel's implicit message set dereferences $ref entries too
- **WHEN** an operation has no `messages[]` narrowing (so every message the channel defines is in scope) and one of the channel's `messages.<name>` entries is itself `{"$ref": "#/components/messages/OrderCreated"}` pointing at an inline message object with a `payload`
- **THEN** that message is included in the operation's message list with its real payload, not silently omitted for lacking an inline `payload` at the channel-map-entry level

#### Scenario: A self-referential schema stops at the cycle, not before
- **WHEN** a message payload schema has a property whose own (possibly nested) `$ref` chain would resolve back to a schema currently being expanded on the same path
- **THEN** resolution expands normally up to that point, and that occurrence is left as an unresolved `{"$ref": ...}` node instead of recursing again

#### Scenario: A sibling key next to a message payload's $ref is not preserved
- **WHEN** a message's payload is `{"$ref": "#/components/schemas/OrderCreated", "description": "override"}`
- **THEN** the resulting schema is `OrderCreated`'s expanded content only — the sibling `description` is discarded, matching AsyncAPI's own Reference Object semantics (contrast with the OpenAPI-side scenario, where sibling keys are merged)

#### Scenario: A sibling key does not survive a cycle or dangling message reference either
- **WHEN** a message reference resolves through a cycle or a dangling pointer, and the unresolved `$ref` node that triggered that outcome happened to carry an extra key alongside `$ref`
- **THEN** the resulting stub carries no leftover sibling content — AsyncAPI's discard-siblings behavior applies the same way whether the reference resolves, cycles, or dangles, not only on the successful-resolve path

#### Scenario: A Message Object with no payload is still the final object, not a stub
- **WHEN** a channel's `messages.<name>` entry (or, absent any `messages[]` narrowing, one of the channel's implicit message set) resolves — after zero or more `$ref` hops — to an inline Message Object that has only `name`/`title`/`summary` fields and no `payload` at all
- **THEN** the resulting message entry has that real `name`/`title`/`summary` with `schema: None`, not a name-only stub and not an entry silently omitted from the message list — the absence of `payload` is not mistaken for "still an unresolved reference"

#### Scenario: A $ref inside example/default/enum/const data is never touched
- **WHEN** a message payload schema has an `example` (or `examples[].payload`, `default`, `enum`, or `const`) value that itself contains a key literally named `$ref` (e.g. `example: {"$ref": "not-a-reference"}`), as arbitrary data an author wrote, not a schema reference
- **THEN** that value is stored exactly as written, untouched by resolution — only `properties`/`items`/`additionalProperties`/`allOf`/`oneOf`/`anyOf`/`not` are ever walked looking for a `$ref` to resolve

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

### Requirement: Message headers schema is resolved against the document's own components
A message's `headers` (a Schema Object, present in both AsyncAPI 2.x and 3.0) that is (or contains) a `$ref` SHALL be resolved against the document's `components.schemas`, recursively, via the same shared resolver `payload` already uses (`resolve-spec-refs`'s `spec_refs.resolve_schema`, `merge_siblings=False` default). A message with no `headers` field SHALL yield no `headers` entry (not an empty-object placeholder).

#### Scenario: A message headers schema that is a $ref is resolved
- **WHEN** a message's `headers` is `{"$ref": "#/components/schemas/EventEnvelope"}` and `#/components/schemas/EventEnvelope` is an inline object schema
- **THEN** the resulting `ApiOperation` message's `headers` has that schema's expanded `type`/`properties`/`required`, not the bare `$ref` string

#### Scenario: A message with no headers yields no headers entry
- **WHEN** a message has no `headers` field at all
- **THEN** the resulting message entry's `headers` is absent/`None`, not an empty schema object

#### Scenario: A self-referential headers schema stops at the cycle, not before
- **WHEN** a message's `headers` schema has a property whose own (possibly nested) `$ref` chain would resolve back to a schema currently being expanded on the same path
- **THEN** resolution expands normally up to that point, and that occurrence is left as an unresolved `{"$ref": ...}` node instead of recursing again, identical to how `payload` already degrades

### Requirement: Operation externalDocs is imported when present
An Operation Object's `externalDocs` (`{description?, url}`, present identically in both AsyncAPI 2.x and 3.0) SHALL be parsed into the resulting `ApiOperation.external_docs`. An operation with no `externalDocs`, or an `externalDocs` object missing `url`, SHALL yield an empty `external_docs`.

#### Scenario: Operation externalDocs is imported
- **WHEN** an operation (either AsyncAPI version) has an `externalDocs` object with a `url` and a `description`
- **THEN** the resulting `ApiOperation.external_docs` has that `url` and `description`

#### Scenario: Operation externalDocs without a url is dropped
- **WHEN** an operation's `externalDocs` object has a `description` but no `url`
- **THEN** the resulting `ApiOperation.external_docs` is empty, and the rest of the operation still imports normally

#### Scenario: A malformed headers or externalDocs block does not abort the operation's import
- **WHEN** a channel/operation's `headers` or `externalDocs` block is malformed in a way that raises during parsing
- **THEN** that one channel/operation is logged and skipped, and the rest of the spec's operations still import normally, matching this parser's existing "one bad operation doesn't blank the API" posture
