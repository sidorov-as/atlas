## Purpose

API Operations is the `Operation` sub-resource of the `api` Entity Kind, owned by the `atlas.apis` plugin. It captures AsyncAPI-like documentation (channel address/protocol, direction, operation key, message payload shape) for individual operations of an AsyncAPI document, and the UI to browse it, without making `Operation` its own registered Entity Kind.

## Requirements

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
An `Operation` SHALL store `channel_address`, `channel_protocol` (when resolvable), `direction`, `operation_key`, an optional `operation_id`/`summary`/`description`, optional `tags`, an optional `external_docs` link, and a `message` payload shape whose entries may each carry an optional resolved `headers` schema alongside their existing `schema`/`example`.

#### Scenario: Operation with no resolvable protocol
- **WHEN** an Operation's channel protocol cannot be resolved from the source document
- **THEN** `channel_protocol` is stored empty and the Overview tab omits the protocol indicator rather than showing a blank/placeholder value

#### Scenario: Operation with multiple message shapes
- **WHEN** an Operation's channel carries more than one distinct message shape
- **THEN** its Message tab lets the user select among them, showing each one's schema and example

#### Scenario: Operation with an externalDocs link
- **WHEN** an Operation's source document declares an `externalDocs` object with a `url` for that operation
- **THEN** `external_docs` is stored with that `url` (and `description`, when present)

#### Scenario: Operation with no externalDocs
- **WHEN** an Operation's source document declares no `externalDocs` for that operation
- **THEN** `external_docs` is stored empty and the Overview tab shows no external docs link

#### Scenario: Message with a resolved headers schema
- **WHEN** an Operation's message declares a `headers` schema in the source document
- **THEN** that message's stored entry includes the resolved `headers` schema alongside its `schema`/`example`

#### Scenario: Message with no headers
- **WHEN** an Operation's message declares no `headers` in the source document
- **THEN** that message's stored entry has no `headers` value, and the Message tab shows no Headers section for it

### Requirement: API detail page lists its operations grouped by channel
An API's detail page SHALL show its Operations grouped into sections by `channel_address`, each section showing a summary of how many publisher and how many subscriber roles exist for that channel across its Operations' linked Services, with Operations nested under their channel's section. This list SHALL show only `active` Operations by default. The list SHALL be paginated by Operation, showing 15 Operations per page by default with a choice of 15, 30, 50 or 100 per page and a page number input; the pagination control SHALL be shown whenever the list is not empty. Grouping SHALL be applied to the Operations of the current page, so a channel whose Operations span a page boundary appears in a section on each of those pages.

#### Scenario: Two operations on the same channel appear in one group
- **WHEN** an API has two Operations sharing the same `channel_address` (e.g. one `send`, one `receive`) and both are on the same page
- **THEN** both appear nested under one channel section, not as two unrelated top-level rows

#### Scenario: Channel group shows a publisher/subscriber summary
- **WHEN** a channel section is rendered
- **THEN** it shows a count of publisher roles and a count of subscriber roles derived from its Operations' linked Services (including each Operation's document-owner role implied by its `direction`)

#### Scenario: Removed operations are excluded from the default list
- **WHEN** an API's operation list is viewed with no removed-operations filter applied
- **THEN** Operations with `status=removed` are not shown

#### Scenario: Long list is split into pages
- **WHEN** an API has 20 active Operations and its operation list is opened
- **THEN** the first 15 Operations are shown, grouped by channel, and the pagination control offers a second page with the remaining 5

#### Scenario: Channel spanning a page boundary
- **WHEN** two Operations of one channel fall on different pages
- **THEN** each page shows that channel's section with the Operations that are on that page

#### Scenario: Filtering returns to the first page
- **WHEN** a user is on the second page and changes the search text, direction or status filter
- **THEN** the list shows the first page of the filtered results

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

### Requirement: Operation page shows Overview and Message tabs
An Operation's detail page SHALL have Overview and Message tabs. The Overview tab SHALL show a documentation summary, channel address/protocol, direction, a compact message summary, and an external docs link when the Operation has one. The Message tab SHALL let the user select among the operation's message shapes (if more than one), view that message's schema and example, and — when that message declares a `headers` schema — a Headers section showing that schema.

#### Scenario: Overview shows the implied document-owner role
- **WHEN** an Operation's Overview is displayed and its API has a known `apiProvidedBy` Service
- **THEN** that Service is shown with a role derived from the Operation's `direction` (publisher for `send`, subscriber for `receive`), without requiring a `ServiceOperationUsage` row for it

#### Scenario: Overview shows an external docs link when present
- **WHEN** an Operation has a non-empty `external_docs`
- **THEN** the Overview tab shows a link using that `url` (and `description`, when present)

#### Scenario: Overview omits the external docs link when absent
- **WHEN** an Operation has no `external_docs`
- **THEN** the Overview tab shows no external docs link, rather than an empty placeholder

#### Scenario: Message tab shows a Headers section only when the message has one
- **WHEN** the Message tab's selected message has a resolved `headers` schema
- **THEN** a Headers section is shown alongside the existing Payload section, rendered with the same schema viewer

#### Scenario: Message tab omits the Headers section when the message has none
- **WHEN** the Message tab's selected message has no `headers`
- **THEN** no Headers section is shown for it, unlike the Payload section which always renders (with its own "No schema" fallback when empty)

### Requirement: Direction is not distinguished by color alone
Direction badges (`Send`/`Receive`) SHALL always include the direction text alongside any semantic color, never color alone, and SHALL use this vocabulary rather than `Publish`/`Subscribe`.

#### Scenario: Direction badge includes text
- **WHEN** a `send` Operation's direction badge is rendered
- **THEN** the badge displays the text "Send" regardless of its background color

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

### Requirement: Operation not found is distinguished from other failures
Requesting a nonexistent or removed Operation SHALL show a distinct "not found" state (with a link back to its API), separate from a general documentation-load failure.

#### Scenario: Nonexistent operation id
- **WHEN** a user navigates to an Operation id that does not exist
- **THEN** the page shows an operation-not-found state with a link back to the parent API, not a generic error

### Requirement: An Operation's channel address is the event name shared across APIs
An Operation's `channel_address` SHALL be the name under which the same real-world event is addressed in every API document that mentions it. Operations from different APIs sharing a `channel_address` SHALL be treated as describing one event, whichever of them publishes and whichever subscribes.

#### Scenario: Publisher and subscribers of one event share an address
- **WHEN** API X has a `send` Operation, and APIs Y and Z each have a `receive` Operation, all with `channel_address` `rk-a`
- **THEN** the three Operations are treated as one event with one publisher and two subscribers

### Requirement: An Operation records how its event is delivered
An Operation SHALL carry a `delivery` object holding any of `exchange`, `queue` and `vhost`, defaulting to an empty object. `delivery` SHALL describe the delivery channel only and SHALL NOT take part in an Operation's identity, its `operation_key`, or its grouping by `channel_address`. The Operation read model SHALL expose `delivery`.

#### Scenario: Delivery is exposed with the Operation
- **WHEN** an Operation with `delivery` `{"queue": "queue-1"}` is read through the API
- **THEN** the response includes that `delivery` object

#### Scenario: Delivery does not affect grouping
- **WHEN** two Operations in one API share a `channel_address` and differ in `delivery`
- **THEN** they are listed in the same channel section
