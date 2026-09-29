## Context

`atlas_plugin_apis/asyncapi_import.py` parses a deliberately narrow field set — this is unchanged since `import-asyncapi-operations` first built it, and `resolve-spec-refs` (landed today) only touched *how* `payload`/message-identity `$ref`s resolve, not *which* fields get read at all. A Message Object's `headers` (a Schema Object, structurally identical to `payload`) and an Operation Object's `externalDocs` (`{description, url}`, standard in both AsyncAPI 2.x and 3.0) are both silently dropped today — `_map_message` only reads `payload`/`examples`/`name`/`title`/`summary`/`contentType`, and `_parse_operation_2x`/`_parse_operation_3x` never look at `externalDocs` at all.

`resolve-spec-refs`'s own proposal flagged this gap by name and deferred it on purpose: "a separate, narrower follow-up once identity/schema resolution lands." The resolver it built (`atlas_plugin_apis/spec_refs.py`, `resolve_schema(node, spec, *, path, merge_siblings)`) is reused here as-is — `headers` needs exactly the same treatment `payload` already gets, no new resolver logic.

A sibling change, `enrich-endpoint-details-from-openapi` (fully planned, not yet implemented), adds the OpenAPI-side counterparts — response `headers`, operation-level `externalDocs`, and resolved `security` — to `ApiEndpoint`. This change is the AsyncAPI-side counterpart for `ApiOperation`, but narrower: `security` is deliberately excluded (see Non-Goals) because AsyncAPI's `security` lives only on the Server Object, not the Operation Object, so there's no direct per-operation equivalent to port.

## Goals / Non-Goals

**Goals:**
- Resolve `message.headers` (2.x and 3.0) via the existing shared `spec_refs.resolve_schema`, exactly like `payload` already is, and store it on the mapped message entry.
- Parse an Operation Object's `externalDocs` (2.x and 3.0, identical shape in both) into a new `ApiOperation.external_docs` column.
- Render both: a "Headers" section in `OperationMessageTab.tsx` (reusing `EndpointSchemaViewer`, no component changes needed — the same precedent `resolve-spec-refs`'s own frontend verification established for the payload schema) and an External docs link in `OperationOverviewTab.tsx`.

**Non-Goals:**
- `security` — AsyncAPI declares `security` only on the Server Object (confirmed against the real seeded `test-asyncapi` spec: `servers.production.security: [$ref: '#/components/securitySchemes/clientCertificate']`), never per-operation. There is no "operation overrides document security" concept to resolve the way `enrich-endpoint-details-from-openapi`'s Decision 3 does for OpenAPI. A server-level equivalent would need its own resolution rule (most naturally mirroring `_resolve_protocol_2x`/`_resolve_protocol_3x`'s existing "only when the channel's servers list has exactly one candidate" pattern, living on `ApiOperation` the same way `channel_protocol` already does, not on `ApiDetails`) — deliberately out of scope for this change.
- `message.correlationId` — a pointer (`{description, location: "$message.header#/correlationId"}` runtime expression) naming which header field holds the correlation ID, not itself content-bearing. Lower value than the header schema's actual content; deferred.
- Operation-level `bindings` — protocol-specific (amqp/kafka/mqtt each define a different bindings object), materially higher effort, no identified UX gap. Deferred, matching `enrich-endpoint-details-from-openapi`'s own posture toward AsyncAPI bindings.
- Channel-level `title`/`summary`/`description` — genuinely undecided, not resolved as in- or out-of-scope during exploration; see Open Questions.
- Any vendor/custom extension (`x-catalog`, etc.) — out of scope, consistent with `resolve-spec-refs`'s own Non-Goals.

## Decisions

### 1. `headers` reuses `spec_refs.resolve_schema` directly — no new resolver code
**Decision:** In `_map_message`, alongside the existing `schema = spec_refs.resolve_schema(payload, spec) if isinstance(payload, dict) else None` line, add `headers = spec_refs.resolve_schema(message.get('headers'), spec) if isinstance(message.get('headers'), dict) else None`, and include it as a new `headers` key in the mapped message dict.

**Why:** `headers` is a Schema Object with identical semantics to `payload` — same recursive `$ref` resolution, same cycle/dangling-pointer safety, same `merge_siblings=False` default (AsyncAPI's Reference Object semantics apply equally to both). `spec_refs.py` was explicitly built as a shared, format-agnostic resolver (`resolve-spec-refs` design.md Decision 1) precisely so a second AsyncAPI call site like this one costs nothing beyond wiring, not a design decision.

**Alternative considered:** A headers-specific resolution helper. Rejected: would duplicate `spec_refs.resolve_schema` for zero behavioral difference.

### 2. `external_docs` is a new top-level `ApiOperation` column, not nested inside `message`
**Decision:** Add `external_docs = models.JSONField(default=dict, blank=True)` to `ApiOperation`, storing `{"description": str, "url": str}` (empty dict when absent). Add `external_docs` to `ParsedOperation` and `_OPERATION_DOC_FIELDS` so the existing upsert diffing (`_upsert_operation`) picks it up for free, the same way `tags`/`deprecated` already do.

**Why:** `externalDocs` is spec'd at the Operation Object level, describing the whole operation, not any one message — nesting it inside `message` (a list, possibly empty or multi-entry) would have no well-defined slot to live in. A new top-level column follows the exact precedent `tags`/`deprecated`/`channel_protocol` already establish for "a scalar/structured operation-level fact." `ApiOperation` is not on the `catalog` app label the way `ApiDetails` is (its migrations already live under `plugins/apis/backend/atlas_plugin_apis/migrations/`, confirmed against `0003_apioperation_deprecated.py`), so this needs a single ordinary migration in the plugin's own migrations directory — none of `enrich-endpoint-details-from-openapi`'s cross-app-label migration-location care is needed here.

**Alternative considered:** Store `external_docs` as a key on every entry of the `message` list (duplicating it per message). Rejected: it's a fact about the operation, not about any message; duplicating it per message (including zero times, for a message-less operation) is a worse shape than one column.

### 3. `externalDocs` parsing is version-uniform — no 2.x/3.0 branching
**Decision:** Both `_parse_operation_2x` and `_parse_operation_3x` read `operation.get('externalDocs')` identically: if it's a dict with a non-empty `url`, store `{"description": externalDocs.get('description') or '', "url": externalDocs['url']}`; otherwise `{}`.

**Why:** AsyncAPI 2.x and 3.0 define the Operation Object's `externalDocs` with the same shape (`{description?, url}`) — unlike `direction`/channel lookup, which genuinely differ between the two versions and already branch in this parser, there's nothing version-specific to resolve here.

### 4. Malformed `headers`/`externalDocs` degrade the same way every other per-operation field already does
**Decision:** No new error handling. A malformed `headers` block or a `externalDocs` without a `url` is caught by the existing per-channel/per-operation `try`/`except` in `_parse_channels_2x`/`_parse_operations_3x` — that one operation is logged and skipped, the rest of the spec still imports, identical to how a malformed `$ref` chain already degrades (`resolve-spec-refs` task 3.5 applied the same reasoning).

**Why:** This parser's established posture (every design in this plugin's history, going back to `import-openapi-endpoints` Decision 5) is "one bad operation doesn't blank the API" — nothing about `headers`/`externalDocs` warrants a different rule.

### 5. Frontend: Headers section only renders when present; External docs link only when present
**Decision:** `OperationMessageTab.tsx` renders a "Headers" section (same treatment as the existing "Payload" section — a labeled `<Text variant="subheader-2">` heading plus `<EndpointSchemaViewer schema={message.headers} />`) **only when `message.headers` is non-null** — unlike Payload, which always renders its section (showing `EndpointSchemaViewer`'s own "No schema" fallback when null), Headers is omitted entirely when absent, since most messages won't declare headers and an always-present "Headers: No schema" line would be pure noise for the common case. `OperationOverviewTab.tsx` renders an External docs link only when `operation.externalDocs?.url` is present, matching the existing `channelProtocol`/`provider` conditional-rendering pattern already in that file.

**Why:** Payload is the primary, expected content of a message (every message documents *something* to consume), so showing its absence is informative; headers is optional envelope metadata most messages won't declare, so showing its absence adds no information and just adds a permanent extra line to every message's tab.

## Risks / Trade-offs

- **[Risk]** `EndpointSchemaViewer`'s root call always auto-expands (`SchemaNode`'s `useState(depth < 1)`), so a message with both a documented `payload` and a documented `headers` block (like the real seeded `test-asyncapi`/"Orders Events API" `OrderCreated` message: 7 header fields plus a multi-property payload) shows two fully-expanded property lists at once, more visual weight per message tab than today. → **Mitigation:** accepted; reusing `EndpointSchemaViewer` unchanged (no new collapse mechanism) matches this plugin's "no component changes needed" precedent, and headers content in practice is a flat handful of envelope fields (ids/timestamps), not deeply nested — revisit only if a real spec's headers block proves unwieldy, the same "real evidence" threshold this plugin already applies elsewhere.
- **[Risk]** Adding `external_docs` as a new `ApiOperation` column is a migration on a table re-upserted on every spec sync. → **Mitigation:** `JSONField(default=dict, blank=True)` needs no backfill, identical to how `tags = ArrayField(..., default=list, blank=True)` already works on the same model and how `enrich-endpoint-details-from-openapi`'s equivalent `ApiEndpoint` columns are planned.
- **[Risk]** This is the third place `spec_refs.resolve_schema` gets called from (OpenAPI schemas, AsyncAPI `payload`, now AsyncAPI `headers`) — if a future change needs per-call-site behavior (e.g. a different `merge_siblings` for headers than payload), the current call sites don't parameterize that per-field, only per-importer. → **Mitigation:** not a real risk today — headers and payload both use AsyncAPI's `merge_siblings=False` default, so no divergence exists yet; noted only so a future reader isn't surprised the two calls look identical.

## Migration Plan

- New migration under `plugins/apis/backend/atlas_plugin_apis/migrations/` adding `ApiOperation.external_docs` (`JSONField(default=dict, blank=True)`) — no data migration, no backfill.
- No model change needed for `headers`: it lives inside the existing `ApiOperation.message` JSON list, which already has no fixed schema contract beyond what `api/schemas.py` promises.
- No backfill for either field: an existing API's stored `ApiOperation` rows keep today's shape (no `headers` in their message entries, no `external_docs`) until that API's spec next re-syncs (create, patch, or the next periodic `spec_url` refresh) — the same accepted one-time gap `resolve-spec-refs` and both archived AsyncAPI/OpenAPI import designs already documented for their own rollouts.
- Rollback: revert the code and the migration. Rows already re-synced with the new fields are ordinary rows indistinguishable from what a future sync (with the reverted code) would produce again.

## Open Questions

- **Channel-level `title`/`summary`/`description`:** should this change also parse and render the channel's own `title`/`summary`/`description` (distinct from the operation's own `description`, which is already parsed)? Flagged as a real gap by `resolve-spec-refs`'s proposal alongside `headers`/`externalDocs`, but not resolved as in- or out-of-scope during this change's exploration — the user confirmed `headers` + `externalDocs` explicitly and left this one open. Leaning toward a future, even narrower follow-up rather than folding it in here, since it's channel-scoped (potentially shared across multiple operations on the same channel) rather than operation-scoped like everything else in this change — revisit before implementation if it should be bundled in instead.
