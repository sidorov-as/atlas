## Why

`add-endpoint-dependency-explorer` shipped `ApiEndpoint`/`ServiceEndpointUsage` as a fully-featured child resource of `API` (documentation tabs, consumers graph, Link/Unlink), but deliberately deferred OpenAPI import as a Non-Goal — endpoint documentation is entered only through Django admin or seed fixtures today. `spec_fetch.apply_api_spec_source`/`resolve_api_spec_url` already fetch and store an API's `spec_content` verbatim (`api-spec-documents` spec), but nothing parses `paths`/`operations` out of it. As a result, an `openapi`-typed API with a real spec URL has zero endpoints unless someone hand-authors them, which defeats the point of pointing Atlas at a live spec: the impact-analysis value `add-endpoint-dependency-explorer` was built for (consumers graph, Linked Services) has no data to work with until a human transcribes the spec by hand.

## What Changes

- Add an OpenAPI (2.0 and 3.x) parser that turns an `openapi`-typed API's `spec_content` into `ApiEndpoint` rows: `method`, `path`, `operationId`, `summary`, `description`, `deprecated`, `tags`, request (path/query/header parameters, body content-type/schema/example), and responses (status code, description, content-type, schema, example) — matching the exact shapes `EndpointRequestOut`/`EndpointResponseOut` already expose.
- Wire this parser into the single point where `ApiDetails` is written, so it runs identically after a user-initiated create/patch (`atlas_plugin_apis.api.views` → `ApiKindHandler`) and after the ingestor's periodic `spec_url` refresh (`atlas_plugin_ingestion.pipeline` → `due_for_spec_refresh`) — no call site has to remember to invoke it separately.
- Upsert by the existing `(api, method, path)` identity: new operations create `ApiEndpoint` rows, changed operations update the existing row (id and any `ServiceEndpointUsage` links stay stable), operations that disappear from a re-parsed spec are soft-removed (`status='removed'`) rather than deleted, and a previously-removed operation that reappears is revived to `active`.
- `$ref` values inside parameter/body/response schemas are stored verbatim (unresolved) — the existing `EndpointSchemaOut.ref`/frontend `EndpointSchemaViewer` already render an unresolved `$ref` label, so this needs no new frontend work and no `components/schemas` resolution/circular-ref handling.
- A spec that fails to parse as OpenAPI (malformed `paths`, unrecognized version, etc.) never raises out of the save/refresh path and never touches existing `ApiEndpoint` rows — it's recorded as a visible failure, mirroring `spec_resolve_failed`'s existing pattern (`api-spec-documents` "Stale spec indicator").
- **BREAKING (behavioral, not API-breaking):** for `openapi`-typed APIs, `ApiEndpoint` fields become spec-derived on every successful parse — a manual Django-admin edit to an importer-managed endpoint's documentation fields is overwritten the next time its API's spec resolves. (Non-`openapi`-typed APIs, and endpoints on APIs with `spec_source=none`, are entirely unaffected and remain manually authored.)

## Capabilities

### New Capabilities
- `openapi-endpoint-import`: parsing an API's resolved OpenAPI (2.0/3.x) `spec_content` into `ApiEndpoint` rows, triggered on every successful spec resolution (create, patch, periodic refresh), including the create/update/revive/soft-remove upsert rules and parse-failure handling.

### Modified Capabilities
- `api-endpoints`: "Endpoint documentation is entered administratively in this change" no longer holds universally — for an `openapi`-typed API, `ApiEndpoint` rows are now written by the importer whenever its spec resolves, not only through Django admin/fixtures. The "no self-service create/edit API" guarantee is unchanged (the importer is a system-triggered side effect of saving/refreshing an API's spec, not a client-facing create/edit endpoint), and the soft-removal invariant (`ServiceEndpointUsage` never cascade-deleted) is extended to cover import-triggered removal, not only administrative removal.

## Impact

- **Backend (`plugins/apis/backend/atlas_plugin_apis`):** new `openapi_import.py` module (parser + upsert); `signals.py`'s existing `ApiDetails` `post_save` receiver gains the sync call; `models/api.py` gains sync-status fields (new migration); `admin.py`/`api/schemas.py`/`api/views.py` expose the new failure indicator.
- **Frontend (`plugins/apis/frontend`):** `ApiSpecPanel.tsx` (or the API detail page) gains an "Endpoint sync failed" indicator alongside the existing "Stale spec" label; the Endpoints list may need a subtler affordance distinguishing import-managed vs. manually-authored endpoints (open question for design).
- **No new runtime dependency** — the parser walks the already-`yaml.safe_load`-parsed spec dict directly rather than adding an OpenAPI object-model library.
- **Ingestion plugin (`plugins/ingestion`):** no code change expected — `due_for_spec_refresh` keeps calling `resolve_api_spec_url`/`details.save(...)` exactly as today; the sync rides the same `post_save` signal `recompute_relations` already rides.
- **Seed data (`seed_booking_demo.py`):** unaffected by this change (Non-Goal here) — its hand-authored `_template_endpoints()` docs may now visibly drift from what the importer would produce for the same spec text; flagged as a follow-up, not fixed in this change.
