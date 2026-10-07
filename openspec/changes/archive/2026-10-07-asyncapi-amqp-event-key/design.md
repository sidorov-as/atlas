## Context

The AsyncAPI import (`atlas_plugin_apis/asyncapi_import.py`) turns each channel operation into an `ApiOperation`. `channel_address` comes straight from the document: the 3.x `channel.address`, or the 2.x channel key. Elsewhere the model already treats `channel_address` as the cross-API name of an event: the publishers/subscribers graph and `/consumers` aggregate every Operation sharing it (`api/views.py`, `consumers.py`), the participant of each Operation is its API's `apiProvidedBy` provider with a role implied by `direction`, and participants are de-duplicated by (service, role).

Real AMQP documents do not follow that convention:

- 3.x publisher documents name the channel and the operation after the exchange; the routing key is only in the operation's `bindings.amqp.cc`.
- 3.x subscriber documents name them after the subscriber's own queue; `cc` again holds the key. The exchange is absent from the document.
- 2.x channel keys are `<routing key>:<exchange>:<Publisher|HandleEvent>`, there is no channel `address`, and `cc` is a string on the `publish`/`subscribe` block.

Facts measured on the real documents that shape the decisions: `cc` always holds exactly one key; no operation has more than one channel; no channel has more than one message; all documents use AMQP; a key is seen with two different exchanges exactly once; most 3.x operations (queue channels) have no exchange; two operations of one document never share a key and direction.

## Goals / Non-Goals

**Goals:**
- Operations that describe the same AMQP event in different documents share one `channel_address`, so the existing graph shows its publishers and subscribers together.
- Keep each Operation's identity (`operation_key`, `id`) stable.
- Keep the delivery details (exchange, queue, vhost) instead of discarding them.
- Stop `removed` Operations from contributing participants to a graph.

**Non-Goals:**
- Alias or separator normalization of routing keys, topic-wildcard matching, an event entity of its own.
- Warning about unused message schemas.
- Correcting documents whose generator inverts 2.x `publish`/`subscribe`.
- Relabeling the Operation page, migrating existing data (the catalog is re-imported from scratch).

## Decisions

### 1. The event key replaces `channel_address`; no new identity column

`channel_address` stays the grouping key and now holds the event key for AMQP operations.

Alternatives: (a) a separate `event_key` column with `channel_address` kept as in the document — the graph, search, MCP tools, `find_operations` and flows' `event_ref` would all need rewiring for a distinction the product does not use; (b) an Event entity kind — a different product, not needed for the graph; (c) store `cc` as a list and group by array membership — `cc` is always a single key in practice and arrays would complicate the graph query and the "one row, one event" reading.

Chosen: the smallest change that uses the semantics already in the model.

Trade-off: the document's own channel address is no longer stored for AMQP operations. The queue and exchange it usually carried are kept in `delivery` instead.

### 2. Event identity is `cc` alone, not (exchange, `cc`)

A routing key only has meaning inside its exchange, so a pair would be more correct in theory. In the data the pair cannot be derived for subscribers (the exchange is not in the document for 44 of 73 3.x operations), and a key has two exchanges exactly once. Using the pair would split most real events.

Alternatives: pair as identity with the exchange optional — events with and without an exchange would never merge; per-vhost scoping — no key occurs in more than one vhost, no benefit.

Risk: two real events sharing a key on different exchanges merge. Accepted and recorded; `delivery.exchange` keeps the information to tell them apart later.

### 3. A protocol-bound adapter with a fallback, not AMQP logic in the parser

Add a small function that, for an AMQP operation, returns the event key and a `delivery` object from the operation and its channel; the existing parsers call it and otherwise keep their behavior. The protocol is the one the parser already resolves (`channel_protocol`, a single top-level server in 2.x, a referenced server in 3.x). When the protocol is unresolved, the adapter applies only if the operation actually carries `bindings.amqp`.

Alternatives: parsing the key out of the 2.x channel name — brittle and unnecessary since `cc` is present; always reading `cc` regardless of protocol — would reinterpret other protocols' bindings.

The adapter accepts `cc` as a list (3.x) or a string (2.x), trims, ignores empty values, and takes the first usable value; when there is none it returns nothing and the caller uses the channel address. Wildcards are not special.

### 4. `operation_key` is left alone

3.x keeps the `operations` map key; 2.x keeps `{channel key}-{direction}`. This keeps the upsert identity stable when the event key changes, and avoids collisions: a publisher and a listener of one key in one 2.x document are on different channel keys (`:Publisher` vs `:HandleEvent`), so their `operation_key` values differ even though their `channel_address` is equal.

Alternative: derive `operation_key` from the event key — would collide in that case and move identities on every key change.

### 5. `delivery` is a single JSON object

`{exchange?, queue?, vhost?}`, empty object by default. A single object is enough because no document has two operations on one key and direction; a list would only matter if one operation could map to several delivery channels, which the data does not show. It is documentation, not identity: it is not part of any uniqueness constraint or grouping. It is a document-owned field refreshed on every sync alongside the existing ones, and it needs one schema migration.

### 6. Active-only graph aggregation

`OperationConsumersController` and `channel_participants` collect operations by `channel_address` with no status filter, so a `removed` Operation keeps its owner and linked Services in the graph. Filter the aggregation to `status=active`. Links stay stored on the removed row (unchanged lifecycle rules); they are simply not shown on the channel graph while the Operation is removed. If the viewed Operation is itself removed, the Linked Services tab already warns; the channel graph shows the other active Operations of the channel.

Alternative: leave removed operations in and mark them — more UI and a decision the product has not made.

### 7. 2.x direction is not changed here

The importer keeps `publish` → `receive` and `subscribe` → `send`. Observed generator output uses `publish` for "this service publishes", so after this change 2.x owners of those documents would still be shown as subscribers. That is corrected where the documents are produced; changing the mapping in Atlas would break correct 2.x documents and the codified rule.

## Risks / Trade-offs

- [Two real events with the same key on different exchanges merge] → accepted; `delivery.exchange` is retained for a later split.
- [Wildcard subscriptions (`orders.event.#`) do not connect to concrete publishers] → known limitation, seven operations in the observed data; pattern matching can be added later without changing the model.
- [The document's own channel address is no longer shown for AMQP operations] → exchange and queue live in `delivery`; fallback keeps the old value whenever `cc` is missing.
- [Events lost by the document generator are still absent from the catalog] → outside Atlas; the import can only reflect what the documents contain. Acceptance is therefore stated against what the documents contain.
- [A removed Operation stops showing on the channel graph, so a team that relied on a removed link loses it from view] → the link row is kept and visible on that Operation's Linked Services tab with the removed warning.
- [Name drift (different wording of the same event) stays unsolved] → needs an explicit alias mechanism, out of scope.

## Migration Plan

1. Add the `delivery` column (default empty object) with a migration.
2. Deploy the adapter and the active-only aggregation.
3. Re-import the catalog from scratch. For a catalog that is not reset, a re-sync of each AsyncAPI API updates rows in place when `operation_key` matches (`channel_address` and `delivery` change, `id` and links stay).
4. Rollback: revert the code; the extra column is harmless. Operations imported with event keys stay until the next re-import with the previous code.

## Open Questions

- Four 3.x operations have no key in the reference graph and nine 2.x blocks in one service are absent from it. They do not affect the design but should be checked against the acceptance numbers before sign-off.
