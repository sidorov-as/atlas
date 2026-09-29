## ADDED Requirements

### Requirement: Operation is a child resource of API, not a registered Entity Kind
An `Operation` SHALL belong to exactly one `API` entity and SHALL NOT be a registered Entity Kind — it has no `kind_id`, no independent owner/team/tags/visibility, and no top-level catalog entity route; it inherits owner/domain/visibility from its API and is addressed only via routes nested under that API.

#### Scenario: Operation has no top-level entity route
- **WHEN** a user has an Operation's id
- **THEN** there is no `/catalog/entities/operation/{id}`-style route for it; it is only reachable via `/apis/{apiId}/operations/{operationId}`

#### Scenario: Operation documentation displays its API's owner/domain/visibility
- **WHEN** an Operation's Overview is displayed
- **THEN** the Owner, Domain, and Visibility shown are the parent API's values, not independently stored on the Operation

### Requirement: Operation has a stable identity independent of its business key
Each `Operation` SHALL have its own identifier that does not change if its channel address or direction changes, and SHALL be unique within its API by `operation_key`.

#### Scenario: Operation id is stable across a channel address edit
- **WHEN** an Operation's `channel_address` is edited after creation (e.g. by a re-import that also preserves its `operation_key`)
- **THEN** its id is unchanged and existing links to it (URLs, `ServiceOperationUsage` rows) remain valid

#### Scenario: Duplicate operation_key within an API is rejected
- **WHEN** a second Operation is created on the same API with the same `operation_key` as an existing Operation
- **THEN** the creation is rejected

#### Scenario: Same channel address is allowed across different APIs
- **WHEN** two different APIs each have an Operation on the same `channel_address`
- **THEN** both creations succeed, since `operation_key` uniqueness is scoped per API, and both Operations are treated as distinct rows describing the same real-world channel

### Requirement: Operation direction is a normalized, spec-version-agnostic fact
An `Operation` SHALL store its `direction` as one of `send` or `receive` — never the literal AsyncAPI 2.x `publish`/`subscribe` field names — representing whether the owning API document's application sends to or receives from the operation's channel.

#### Scenario: An AsyncAPI 2.x publish operation is stored as receive
- **WHEN** an Operation is derived from an AsyncAPI 2.x document's `publish` field on a channel
- **THEN** its stored `direction` is `receive`, reflecting that the application consumes messages from that channel

#### Scenario: An AsyncAPI 2.x subscribe operation is stored as send
- **WHEN** an Operation is derived from an AsyncAPI 2.x document's `subscribe` field on a channel
- **THEN** its stored `direction` is `send`, reflecting that the application produces messages to that channel

#### Scenario: An AsyncAPI 3.0 operation's action maps through unchanged
- **WHEN** an Operation is derived from an AsyncAPI 3.0 document's `operations` entry with `action: send` or `action: receive`
- **THEN** its stored `direction` matches that `action` value exactly

### Requirement: Operation captures channel and message documentation
An `Operation` SHALL store `channel_address`, `channel_protocol` (when resolvable), `direction`, `operation_key`, an optional `operation_id`/`summary`/`description`, optional `tags`, and a `message` payload shape.

#### Scenario: Operation with no resolvable protocol
- **WHEN** an Operation's channel protocol cannot be resolved from the source document
- **THEN** `channel_protocol` is stored empty and the Overview tab omits the protocol indicator rather than showing a blank/placeholder value

#### Scenario: Operation with multiple message shapes
- **WHEN** an Operation's channel carries more than one distinct message shape
- **THEN** its Message tab lets the user select among them, showing each one's schema and example

### Requirement: API detail page lists its operations grouped by channel
An API's detail page SHALL show its Operations grouped into sections by `channel_address`, each section showing a summary of how many publisher and how many subscriber roles exist for that channel across its Operations' linked Services, with Operations nested under their channel's section. This list SHALL show only `active` Operations by default.

#### Scenario: Two operations on the same channel appear in one group
- **WHEN** an API has two Operations sharing the same `channel_address` (e.g. one `send`, one `receive`)
- **THEN** both appear nested under one channel section, not as two unrelated top-level rows

#### Scenario: Channel group shows a publisher/subscriber summary
- **WHEN** a channel section is rendered
- **THEN** it shows a count of publisher roles and a count of subscriber roles derived from its Operations' linked Services (including each Operation's document-owner role implied by its `direction`)

#### Scenario: Removed operations are excluded from the default list
- **WHEN** an API's operation list is viewed with no removed-operations filter applied
- **THEN** Operations with `status=removed` are not shown

### Requirement: Operation documentation is entered administratively in this change
Creating or editing an `Operation`'s documentation SHALL NOT be available through any self-service, permission-gated API or UI; operation data is entered through Django admin or fixtures/seed data.

#### Scenario: No create/edit endpoint exists
- **WHEN** a client requests to create or update an `Operation` through the catalog API
- **THEN** no such operation is exposed — only reading (list, detail) is available

### Requirement: Removing an operation is soft, preserving existing dependency links
Removing an `Operation` SHALL set its status to `removed` rather than deleting its row, and SHALL NOT delete any `ServiceOperationUsage` rows that reference it. A `removed` Operation SHALL remain visible in a dedicated section separate from an API's default (active) operation list, and any view of its existing Service links SHALL show a visible warning that the operation has been removed.

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

### Requirement: Operation page shows Overview and Message tabs
An Operation's detail page SHALL have Overview and Message tabs. The Overview tab SHALL show a documentation summary, channel address/protocol, direction, and a compact message summary. The Message tab SHALL let the user select among the operation's message shapes (if more than one) and view that message's schema and example.

#### Scenario: Overview shows the implied document-owner role
- **WHEN** an Operation's Overview is displayed and its API has a known `apiProvidedBy` Service
- **THEN** that Service is shown with a role derived from the Operation's `direction` (publisher for `send`, subscriber for `receive`), without requiring a `ServiceOperationUsage` row for it

### Requirement: Direction is not distinguished by color alone
Direction badges (`Send`/`Receive`) SHALL always include the direction text alongside any semantic color, never color alone, and SHALL use this vocabulary rather than `Publish`/`Subscribe`.

#### Scenario: Direction badge includes text
- **WHEN** a `send` Operation's direction badge is rendered
- **THEN** the badge displays the text "Send" regardless of its background color

### Requirement: Operation not found is distinguished from other failures
Requesting a nonexistent or removed Operation SHALL show a distinct "not found" state (with a link back to its API), separate from a general documentation-load failure.

#### Scenario: Nonexistent operation id
- **WHEN** a user navigates to an Operation id that does not exist
- **THEN** the page shows an operation-not-found state with a link back to the parent API, not a generic error
