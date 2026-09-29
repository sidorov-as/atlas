## MODIFIED Requirements

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
