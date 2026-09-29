## Context

`openapi_import.py` is a hand-rolled walker over `yaml.safe_load`-parsed OpenAPI 3.x/Swagger 2.0 spec dicts (no OpenAPI object-model library, `import-openapi-endpoints` design.md Decision 3), triggered by `_sync_endpoints_on_save` (`signals.py`) on every `ApiDetails` save, calling `sync_endpoints_from_spec(details)` which parses `details.spec_content` and both upserts `ApiEndpoint` rows and sets `details.endpoints_synced_at`/`endpoints_sync_failed` directly on the same `ApiDetails` instance it was handed.

`ApiDetails` (`plugins/apis/backend/atlas_plugin_apis/models/api.py`) keeps `app_label = 'catalog'` — a deliberate pre-existing-table-move decision recorded in its own docstring — so migrations for new fields on this model live under `core/backend/server/apps/catalog/migrations/`, not `plugins/apis/backend/atlas_plugin_apis/migrations/`.

The AsyncAPI side (`asyncapi_import.py`) already has precedent for exactly the kind of resolution this change needs for OpenAPI: `_resolve_protocol_2x`/`_resolve_protocol_3x` populate `channel_protocol` **only when the document's `servers` map has exactly one candidate** (`openapi-endpoint-import` sibling spec `asyncapi-operation-import`'s "Channel protocol is resolved only when unambiguous" requirement) — otherwise left empty rather than guessed. No equivalent resolution exists on the OpenAPI side today; `ApiDetails` has no server/base-URL/protocol field at all, and nothing in the frontend (`ApiSpecPanel.tsx`, `OpenApiViewer.tsx`, `ApiSpecDocViewer.tsx`, `AsyncApiViewer.tsx`) surfaces it.

## Goals / Non-Goals

**Goals:**
- Render `schema.format`/`schema.enum` (already parsed, currently dropped by `EndpointParameterTable`) for path/query/header parameters.
- Show an aggregated Consumes/Produces summary on the Details card, computed client-side from already-present per-request/response content types.
- Parse and store per-response `headers`, per-operation `externalDocs`, and a resolved `security` label set; render them on the Response tab / Overview Details card.
- Resolve the document's `servers` (3.x) / `host`+`basePath`+`schemes` (2.0) into a base URL + protocol on `ApiDetails`, only when unambiguous, mirroring the AsyncAPI precedent above.

**Non-Goals:**
- AsyncAPI channel bindings or AsyncAPI operation-level `security` — a different, larger section of that spec with no identified UX gap yet; left for a future change if one emerges.
- Per-operation `servers` overrides (a rare 3.x feature) — only the document-level `servers` is resolved.
- Any layout change to where the Details card sits — that's `restructure-dependency-graph-layout`, which this change is sequenced after.

## Decisions

### 1. `servers`/base-URL/protocol resolution lives in `sync_endpoints_from_spec`, mirrors the AsyncAPI "unambiguous only" rule
**Decision:** Add a `_resolve_servers(spec, version)` step inside `openapi_import.py`, called from `sync_endpoints_from_spec(details)` alongside the existing `parse_operations` call. It returns a base URL + protocol only when the spec declares exactly one server (3.x `servers` list of length 1, or 2.0's single `host`+`schemes[0]`); otherwise both are left empty. The two new fields are set directly on the `details` instance already being saved (`endpoints_synced_at` etc.), in the same `details.save(update_fields=[...])` call, rather than a second write.

**Why:** `asyncapi-operation-import`'s existing "resolve only when unambiguous" rule (`asyncapi-operation-import` spec, "Channel protocol is resolved only when unambiguous") is the established house answer to "the spec has more than one candidate server" — reusing it keeps the two importers consistent instead of inventing a different ambiguity rule for OpenAPI. Hooking into the same `sync_endpoints_from_spec`/`details.save()` call avoids a second signal-triggered write.

**Alternative considered:** Resolve `servers` lazily on read (in `api/schemas.py`'s output serialization) instead of storing it. Rejected: `spec_content` is raw text; re-parsing it on every API detail-page read to extract two strings is wasted work the existing sync-on-save pattern already avoids for everything else this parser produces.

### 2. Response `headers`/`externalDocs`/`security` go into the existing JSON blobs, not new columns
**Decision:** `headers` is added as a key on each entry of `ApiEndpoint.responses` (JSON), matching how `schema`/`example`/`content_type` already live there. `externalDocs` and resolved `security` are added as top-level keys on `ApiEndpoint.request`... no — `externalDocs` and `security` are operation-level, not request-level, so they become new top-level fields directly on `ApiEndpoint` doc-owned fields (i.e. new model columns: `external_docs = models.JSONField(default=dict, blank=True)`, `security = models.JSONField(default=list, blank=True)`), added to `_ENDPOINT_DOC_FIELDS` alongside `operation_id`/`summary`/etc. so the existing upsert diffing (`_upsert_operation`) picks them up for free.

**Why:** `headers` is naturally per-response, so it nests inside the existing `responses` list entry — no new column needed, `EndpointResponseOut` just gains a `headers` field. `externalDocs`/`security` describe the whole operation, not one response or the request body, so they don't fit inside `request`/`responses`; new top-level `ApiEndpoint` columns (following the exact pattern `deprecated`/`tags` already establish for scalar/list operation-level facts) are more consistent than smuggling them into an unrelated JSON blob.

### 3. `security` is stored as a resolved type-label list, not raw scheme names
**Decision:** `security` resolution reads the operation's effective `security` requirement (falling back to the document's top-level `security` when the operation doesn't override it, per OpenAPI's own inheritance rule) and, for each referenced scheme name, looks it up in `components.securitySchemes` (3.x) / `securityDefinitions` (2.0) to store a small label: `{"type": "oauth2" | "apiKey" | "http", "scheme": "bearer" | ... | None}` per entry — not the raw scheme name, which is spec-author-chosen and not guaranteed to mean anything to a reader (e.g. a scheme literally named `Auth1`).

**Why:** The mockup's Details card shows a human-meaningful label ("OAuth2"), not an arbitrary scheme identifier. Resolving to `type`/`scheme` gives the frontend something renderable without needing to carry the full securityScheme definition (flows, scopes, etc. — out of scope; if scope-level detail is wanted later, that's an additive follow-up, not a breaking change to this shape).

**Alternative considered:** Store the raw `security` array as declared (list of `{schemeName: [scopes]}`) and resolve display labels client-side. Rejected: would require shipping `components.securitySchemes` to the frontend too (currently never parsed or stored at all) just to resolve a label — more new surface for no benefit over resolving once at parse time.

### 4. Parameter `format`/`enum` and aggregated Consumes/Produces are frontend-only
**Decision:** No backend change for these — `EndpointParameterTable.tsx`'s existing `type` column becomes `type` + `format` (e.g. `string (uuid)`) using already-present `schema.format`, with `schema.enum` values shown alongside (e.g. as a tooltip or secondary line) when present. The Details card's Consumes/Produces row is computed by the Overview tab from the endpoint's own `request.body.contentType` and each `responses[].contentType`, deduplicated.

**Why:** Both are already fully present in `EndpointRequestOut`/`EndpointResponseOut`/`EndpointSchemaOut` — no parser or model work is needed, only rendering.

## Risks / Trade-offs

- **[Risk]** `_resolve_servers`'s "unambiguous only" rule means most real-world multi-environment specs (prod/staging/dev servers, a common 3.x pattern) will leave Protocol/Base URL empty, same as `channel_protocol` already does for AsyncAPI. → **Mitigation:** accepted, deliberate consistency with existing house behavior (see `asyncapi-operation-import`'s own scenario "Multiple servers leave protocol unresolved"); not a regression this change introduces.
- **[Risk]** Adding `external_docs`/`security` as new `ApiEndpoint` columns is a schema migration on a table that's re-upserted on every spec sync — need to confirm the migration ships with sane defaults (`default=dict`/`default=list`) so existing rows don't need backfilling before the next sync naturally populates them. → **Mitigation:** Django's `JSONField(default=dict/list, blank=True)` handles this with no backfill migration needed, consistent with how `tags = ArrayField(..., default=list, blank=True)` already works on the same model.
- **[Risk]** Resolving `security` against `components.securitySchemes` at parse time means a scheme lookup failure (a `$ref` to a missing scheme name, a malformed scheme object) needs the same "skip this operation's field, don't abort the whole sync" handling `_parse_operation`'s existing per-operation try/except already gives every other field. → **Mitigation:** no new mechanism needed — `parse_operations`'s existing per-operation `except Exception: logger.warning(...)` wrapper already covers this; a broken `security` block degrades that one field, not the whole parse.
