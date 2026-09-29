## Why

An Endpoint's Overview tab today shows less than what a synced OpenAPI document actually contains. Some of that data is already parsed and stored but not rendered (parameter `format`, `enum`); some is parsed per-field but never aggregated into a summary (per-request/response content types that could roll up into a Consumes/Produces view); and some is never parsed at all despite being standard, useful OpenAPI content (response `headers`, per-operation `externalDocs`, `security`, and the document's `servers`/base URL). The original UX spec this feature was built from (`local/endpoint-dependency-explorer-design-spec.md` §20, `local/endpoint-dependency-explorer-design.png`) shows a Details card with Protocol/Base URL/Consumes/Produces/Security fields that no current field of `ApiEndpoint` or `ApiDetails` actually backs.

## What Changes

**No backend change required (frontend-only):**
- `EndpointParameterTable` shows each parameter's `schema.format` alongside its `type` (e.g. `string (uuid)`), and its `schema.enum` values when present, instead of dropping both.
- The Details card shows an aggregated Consumes/Produces summary computed from the endpoint's already-present request/response `contentType` values.

**Backend parser + model extension (OpenAPI 3.x / Swagger 2.0, same effort tier as existing request/response parsing):**
- `openapi_import.py` parses each response's `headers` (3.x) into the stored response shape; rendered in the Response tab.
- `openapi_import.py` parses an operation's `externalDocs` (3.x and 2.0 both support it); rendered as a link on the Overview tab.
- `openapi_import.py` resolves an operation's effective `security` requirement against the document's `components.securitySchemes` (3.x) / `securityDefinitions` (2.0) into a small label set (e.g. scheme type: `oauth2`, `apiKey`, `http-bearer`); rendered in the Details card.

**API-level parsing (new field on `ApiDetails`, synced alongside endpoint sync, not per-`ApiEndpoint`):**
- `ApiDetails` gains a resolved `servers`/base-URL/protocol field, populated only when the document's `servers` (3.x) / `host`+`basePath`+`schemes` (2.0) are unambiguous — mirroring `asyncapi-operation-import`'s existing "resolve `channel_protocol` only when exactly one server" precedent rather than inventing a new resolution rule. Rendered as Protocol/Base URL in the Details card.

**Non-goals:** AsyncAPI channel bindings and AsyncAPI-side `security` are out of scope for this change — they're a materially different, more complex section of that spec and no UX gap for them has been identified yet, unlike the OpenAPI gaps above which map directly to an already-reviewed mockup. No dedicated graph-explorer or layout work (that's `restructure-dependency-graph-layout`, sequenced before this change).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `api-endpoints`: `Endpoint` documentation gains response headers and per-operation `externalDocs`/resolved `security` fields; the Overview tab's Details section gains Protocol/Base URL/Consumes/Produces/Security; the parameter table shows `format` and `enum`.
- `openapi-endpoint-import`: the parser gains response-header, `externalDocs`, and `security`-resolution parsing (OpenAPI 3.x and Swagger 2.0), and a new unambiguous-`servers`-resolution step feeding `ApiDetails`.

## Impact

- `plugins/apis/backend/atlas_plugin_apis/openapi_import.py` — parser extensions (response headers, externalDocs, security resolution, servers resolution).
- `plugins/apis/backend/atlas_plugin_apis/models/endpoint.py` — no new columns needed if headers/externalDocs/security are added to the existing `request`/`responses` JSON shapes; `plugins/apis/backend/atlas_plugin_apis/models/api.py` (`ApiDetails`) gains the new servers/base-URL/protocol field(s). `ApiDetails` keeps `app_label = 'catalog'` (a pre-existing table move, see its docstring), so the migration for this field addition belongs under `core/backend/server/apps/catalog/migrations/`, not `plugins/apis/backend/atlas_plugin_apis/migrations/` — verify this against current migration state before assuming the file location.
- `plugins/apis/backend/atlas_plugin_apis/api/schemas.py` — extend `EndpointResponseOut` (headers), add `externalDocs`/`security` output shapes, extend the API-level output schema for the new servers field.
- `plugins/apis/frontend/src/components/EndpointParameterTable.tsx` — render `format`/`enum`.
- `plugins/apis/frontend/src/components/EndpointOverviewTab.tsx`, `EndpointResponseTab.tsx` — render the new fields in the Details card and Response tab respectively.
- `plugins/apis/frontend/src/lib/types.ts` — extend `Endpoint`/`EndpointResponse`/`ApiEntity`-adjacent types for the new fields.
- Sequenced after `restructure-dependency-graph-layout`: the Details-card fields added here land into the layout that change establishes, avoiding repositioning the card twice.
