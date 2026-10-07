## Why

Atlas treats an Operation's `channel_address` as the cross-API name of an event: the publishers/subscribers graph aggregates every Operation that shares it, across API documents. Real AMQP documents break that assumption. A publisher document names its channel after the exchange, a subscriber document names its channel after its own queue, and in 2.x the channel key is a composite `<routing key>:<exchange>:<role>`. The routing key that actually identifies the event lives only in `bindings.amqp.cc`, which the importer never reads. Result: one event is represented by an exchange channel plus one channel per subscriber queue, none of which share an address, so the graph shows a single participant instead of every publisher and subscriber.

## What Changes

- Add a protocol-bound AMQP adapter to the AsyncAPI import. It derives the **event key** from the operation's `bindings.amqp.cc` and stores it as the Operation's `channel_address`.
  - 3.x: `cc` is a list on the operation; 2.x: `cc` is a string on the `publish`/`subscribe` block. Both shapes are accepted.
  - Values are trimmed; an empty or whitespace-only value counts as absent. When no usable `cc` exists, the channel's own address (the channel key in 2.x) is used as today.
  - `cc` is the event identity on its own, not the pair (exchange, `cc`). Wildcard values (`*`, `#`) are kept as literal strings; no topic-pattern matching.
  - Only AMQP documents are adapted. Documents for other protocols keep today's behavior.
- `operation_key` is unchanged (3.x operations-map key; 2.x `{channel key}-{direction}`), so re-import identity does not move when the event key changes.
- Add a `delivery` field on `ApiOperation`: one JSON object with the optional `exchange`, `queue` and `vhost` read from the channel's `bindings.amqp`. It carries how the event is delivered; it plays no part in identity.
- The publishers/subscribers graph and the `/consumers` aggregation take part only from `active` Operations. A `removed` Operation no longer contributes its document owner or its linked Services to a channel.
- Document the standing model assumption: `channel_address` is the event name shared across APIs; participants come from each API's `apiProvidedBy` provider with the role implied by `direction`, de-duplicated by (service, role).

Out of scope, deliberately:
- A routing-key alias table or separator normalization. In the real data, keys differing only by `.` versus `_` are different events; observed drift is wording (singular/plural, a missing segment), which no generic rule fixes.
- Warning about unused message schemas. In the observed data most of them belong to shared schema libraries, so the signal is mostly false positives.
- The 2.x `publish`/`subscribe` direction. The importer follows the AsyncAPI mapping already codified; documents from a generator that writes `publish` for "this service publishes" are corrected at the generator, not in Atlas.
- Relabeling the Operation page header, topic-wildcard matching, and data migration (the catalog is re-imported from scratch).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `asyncapi-operation-import`: `channel_address` becomes the event key derived by the AMQP adapter (with fallback to the channel address); `delivery` is populated from the channel's AMQP bindings; `operation_key` stays independent of the event key.
- `api-operations`: an Operation additionally stores `delivery` (exchange, queue, vhost) and its `channel_address` is documented as the event key shared across APIs.
- `operation-service-dependencies`: the channel-scoped graph and `/consumers` aggregation include only `active` Operations.

## Impact

- Backend, `atlas.apis` plugin: `asyncapi_import.py` (adapter, `ParsedOperation`, upsert field list), `models/operation.py` plus a new migration for `delivery`, `api/schemas.py` (Operation read model exposes `delivery`), `api/views.py` and `consumers.py` (active-only aggregation), `extension_points.py` and MCP schemas only where they echo the Operation shape.
- No change to `ServiceOperationUsage`, flows' `event_ref` storage, or the participant de-duplication rule.
- Existing catalogs: Operations whose address changes are updated in place when their `operation_key` matches; the expected rollout is a full re-import.
- Acceptance on reference data: four known events must show publishers/subscribers of 5/8, 5/5, 3/2 and 0/2 respectively after import.
