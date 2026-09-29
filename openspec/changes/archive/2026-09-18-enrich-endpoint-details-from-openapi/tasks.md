## 1. Frontend-only: parameter format/enum and aggregated Consumes/Produces

- [x] 1.1 Update `EndpointParameterTable.tsx`'s "Type" column to render `type` combined with `format` (e.g. `string (uuid)`) when `format` is present.
- [x] 1.2 Add enum-values display to `EndpointParameterTable.tsx` for parameters whose `schema.enum` is present.
- [x] 1.3 Add a Consumes/Produces computation in `EndpointOverviewTab.tsx` (or a small helper) that deduplicates content types across `request.body.contentType` and each `responses[].contentType`, rendered in the Details card.
- [x] 1.4 Update/add tests for `EndpointParameterTable` and `EndpointOverviewTab` covering format+enum rendering and the aggregated Consumes/Produces row.

## 2. Backend: response headers, externalDocs, security parsing

- [x] 2.1 Add `external_docs = models.JSONField(default=dict, blank=True)` and `security = models.JSONField(default=list, blank=True)` to `ApiEndpoint` (`plugins/apis/backend/atlas_plugin_apis/models/endpoint.py`); add both to `_ENDPOINT_DOC_FIELDS` in `openapi_import.py`; generate the migration under `plugins/apis/backend/atlas_plugin_apis/migrations/`.
- [x] 2.2 Parse `responses[code].headers` (3.x) into each response entry in `_map_responses_3x`; confirm whether Swagger 2.0 has an equivalent (`response.headers`) and parse it in `_map_responses_2x` if so.
- [x] 2.3 Parse operation-level `externalDocs` (both versions) in `_parse_operation` into `ParsedOperation.external_docs`.
- [x] 2.4 Implement `security` resolution: read the operation's `security` (falling back to the document's top-level `security` when absent), resolve each referenced scheme name against `components.securitySchemes` (3.x) / `securityDefinitions` (2.0) into `{"type": ..., "scheme": ...}` entries, dropping unresolvable scheme references (log + skip, not fail the operation) — reuse `_parse_operation`'s existing per-operation `except Exception` wrapper in `parse_operations`.
- [x] 2.5 Extend `EndpointResponseOut` (`api/schemas.py`) with `headers`; add `EndpointOut.external_docs`/`.security` output shapes.
- [x] 2.6 Update `EndpointResponseTab.tsx` to render response headers; update `EndpointOverviewTab.tsx`'s Details card to render `externalDocs` (as a link) and `security` (as a label).
- [x] 2.7 Extend `plugins/apis/backend/atlas_plugin_apis/tests/test_openapi_import.py` with cases for headers, externalDocs, security resolution (including the unknown-scheme-dropped and document-level-fallback scenarios from `specs/openapi-endpoint-import/spec.md`), for both OpenAPI 3.x and Swagger 2.0 where applicable.

## 3. Backend: document-level servers → base URL/protocol

- [x] 3.1 Add `resolved_base_url`/`resolved_protocol` (naming TBD at implementation time) fields to `ApiDetails` (`plugins/apis/backend/atlas_plugin_apis/models/api.py`); since `ApiDetails` keeps `app_label = 'catalog'`, generate the migration under `core/backend/server/apps/catalog/migrations/` (verify current migration head there first) rather than under `atlas_plugin_apis`.
- [x] 3.2 Implement `_resolve_servers(spec, version)` in `openapi_import.py`: 3.x resolves only when `servers` has exactly one entry; 2.0 resolves base URL from `host`+`basePath` and protocol only when `schemes` has exactly one entry (base URL may still resolve with protocol left empty per the spec's "Swagger 2.0 multiple schemes leave protocol unresolved" scenario).
- [x] 3.3 Call `_resolve_servers` from `sync_endpoints_from_spec(details)` and include the two new fields in the same `details.save(update_fields=[...])` call that already persists `endpoints_synced_at`/`endpoints_sync_failed` — also added both fields to `signals.py`'s `_SYNC_STATUS_FIELDS` self-write guard (an existing infinite-recursion regression test caught that this was required).
- [x] 3.4 Extend `ApiSpecOut` (`api/schemas.py`) with the two new fields.
- [x] 3.5 Update `EndpointOverviewTab.tsx`'s Details card to render Protocol/Base URL when present, omitted otherwise.
- [x] 3.6 Add tests for `_resolve_servers` covering: single 3.x server resolves, multiple 3.x servers leave both empty, 2.0 single scheme resolves both, 2.0 multiple schemes resolve base URL only.

## 4. Verification

- [x] 4.1 Run the backend test suite for `atlas_plugin_apis` and confirm all new/updated tests pass.
- [x] 4.2 Run the frontend test suite for `plugins/apis/frontend` and confirm all new/updated tests pass.
- [x] 4.3 Manually verify against a real multi-field OpenAPI spec (e.g. the seeded demo data) that: parameter format/enum render, Consumes/Produces aggregate correctly, response headers show on the Response tab, externalDocs links out, security shows a resolved label, and Protocol/Base URL populate only for a single-server API and stay empty for a multi-server one.
