## Why

`asyncapi_import.py` extracts a narrow field set from a Message Object (`name`/`title`/`summary`/`contentType`/`payload`/`example`) and an Operation Object (`operationId`/`summary`/`description`/`tags`/`messages`/`channel_address`/`channel_protocol`/`direction`) — `message.headers` and operation-level `externalDocs`, both standard AsyncAPI 2.x/3.0 content, are silently dropped. `resolve-spec-refs`'s own proposal already flagged this and deferred it on purpose: "New fields not currently modeled at all — `message.headers`, `message.correlationId`, ... message-level `tags`/`externalDocs`, operation-level `bindings`/`externalDocs`, channel-level `title`/`summary`/`description`... Real gaps, but a separate, narrower follow-up once identity/schema resolution lands." That resolution (`spec_refs.resolve_schema`, multi-hop message dereferencing) has now landed — this is that follow-up.

The gap isn't hypothetical: the seeded `test-asyncapi` entity's real "Orders Events API" spec already carries a rich `headers` schema on its `OrderCreated` message (`messageId` as a uuid, `correlationId`, `traceId`, `timestamp` as a date-time, `eventType` with a `const`, `eventVersion`, `producer`) that today's importer throws away entirely — the same category of "real spec content the parser drops" evidence that originally motivated `resolve-spec-refs`.

## What Changes

- **Message headers resolved into a real schema, not dropped:** `message.headers` (a Schema Object, exactly like `payload`) is resolved via the shared `atlas_plugin_apis/spec_refs.py` resolver (`spec_refs.resolve_schema(headers, spec)`, `merge_siblings=False` default — same treatment `payload` already gets) and stored on the mapped message entry. `OperationMessageTab.tsx` renders it in its own labeled section, reusing `EndpointSchemaViewer` the same way the existing payload section already does.
- **Operation-level `externalDocs` parsed and rendered:** both AsyncAPI 2.x and 3.0 support `externalDocs` (`{description, url}`) directly on the Operation Object. Parsed into a new `ApiOperation.external_docs` column (new migration), rendered as a link on `OperationOverviewTab.tsx` — the AsyncAPI-side counterpart to what `enrich-endpoint-details-from-openapi` (sibling change, OpenAPI-only) already plans for `EndpointOverviewTab.tsx`.

**Explicitly not changing:**
- **`security` stays OpenAPI-only.** AsyncAPI declares `security` only on the Server Object (confirmed against the real seeded spec: `servers.production.security: [$ref: '#/components/securitySchemes/clientCertificate']`) — there is no per-operation override to resolve, unlike OpenAPI where an operation can override document-level security. Porting `enrich-endpoint-details-from-openapi`'s per-operation security-label resolution doesn't apply here; a server-level equivalent would need its own design (mirroring `channel_protocol`'s existing "resolve only when the channel's servers list has exactly one candidate" rule) and is deliberately left out of this change's scope.
- **`message.correlationId`** — a pointer/runtime-expression field (`{description, location: "$message.header#/correlationId"}`) naming *which* header holds the correlation ID, not content-bearing itself. Lower value than the header schema's actual content; deferred.
- **Operation-level `bindings`** — protocol-specific (amqp/kafka/mqtt each define a different bindings shape), materially higher effort than this change's other items, no identified UX gap. Deferred, matching `enrich-endpoint-details-from-openapi`'s own posture of deferring AsyncAPI bindings.
- **Channel-level `title`/`summary`/`description`** (distinct from the operation's own `description`) — not resolved as in- or out-of-scope during exploration; left as an Open Question in design.md rather than silently decided either way.
- Any vendor/custom extension (e.g. `x-catalog`) — out of scope entirely, consistent with `resolve-spec-refs`'s own Non-Goals.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `asyncapi-operation-import`: the parser gains `message.headers` schema resolution (via the shared `spec_refs` resolver) and operation-level `externalDocs` parsing, for both AsyncAPI 2.x and 3.0.
- `api-operations`: `Operation`/`OperationMessage` documentation gains a resolved `headers` schema and an `externalDocs` link; `OperationMessageTab`/`OperationOverviewTab` render them.

## Impact

- `plugins/apis/backend/atlas_plugin_apis/asyncapi_import.py` — `_map_message` gains `headers` resolution; `_parse_operation_2x`/`_parse_operation_3x`/`ParsedOperation` gain `external_docs`; `_OPERATION_DOC_FIELDS` gains the new column name.
- `plugins/apis/backend/atlas_plugin_apis/models/operation.py` — `ApiOperation` gains `external_docs = models.JSONField(default=dict, blank=True)`; new migration under `plugins/apis/backend/atlas_plugin_apis/migrations/` (unlike `ApiDetails`, `ApiOperation` is not on the `catalog` app label, so no cross-app migration-location gotcha here).
- `plugins/apis/backend/atlas_plugin_apis/api/schemas.py` — `OperationMessageOut` gains `headers`; `OperationOut` gains `external_docs`.
- `plugins/apis/frontend/src/components/OperationMessageTab.tsx` — renders the resolved `headers` schema via `EndpointSchemaViewer`, alongside the existing payload section.
- `plugins/apis/frontend/src/components/OperationOverviewTab.tsx` — renders `externalDocs` as a link.
- `plugins/apis/frontend/src/lib/types.ts` — extend `OperationMessage`/`Operation` types for the two new fields.
- `plugins/apis/backend/atlas_plugin_apis/spec_refs.py` — reused as-is, no changes.
- `core/backend/server/apps/catalog/management/commands/seed_booking_demo.py` — `ASYNCAPI_SPEC`/`BOOKING_EVENTS_ASYNCAPI_SPEC` (enriched by `resolve-spec-refs`) are natural candidates to extend with a `headers`/`externalDocs` example once this lands, so the demo catalog shows the new fields too — not required for this change to be correct, a follow-up polish item.
- No change to `ApiEndpoint`/`ApiDetails` or the OpenAPI import path — that's `enrich-endpoint-details-from-openapi`'s scope, unaffected by this change.
