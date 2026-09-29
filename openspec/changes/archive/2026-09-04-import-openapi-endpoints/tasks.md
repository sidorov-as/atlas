## 1. Data model

- [x] 1.1 Add `ApiDetails.endpoints_synced_at` (nullable `DateTimeField`) and `ApiDetails.endpoints_sync_failed` (`BooleanField`, default `False`) to `plugins/apis/backend/atlas_plugin_apis/models/api.py`
- [x] 1.2 Generate and check in the new Django migration (purely additive; no changes to `ApiEndpoint`/`ServiceEndpointUsage`)

## 2. OpenAPI parser (`openapi_import.py`)

- [x] 2.1 Create `plugins/apis/backend/atlas_plugin_apis/openapi_import.py`; add a version detector that loads `spec_content` via `yaml.safe_load` and returns which of `openapi: "3.x"` / `swagger: "2.0"` / neither it is
- [x] 2.2 Implement the `paths` walker producing one intermediate operation record per `(method, path)`, common to both versions: `operation_id`, `summary`, `description`, `deprecated`, `tags`
- [x] 2.3 Implement parameter mapping for `in: path|query|header` (both versions) into `EndpointParameterOut` shape; drop `in: cookie` (3.x only) without failing the operation (design.md Decision 4)
- [x] 2.4 Implement 3.x request body mapping: `requestBody.content[contentType].{schema,example}` → `EndpointBodyOut`
- [x] 2.5 Implement 2.0 request body mapping: `in: body` parameter's `schema` → `EndpointBodyOut` (content type from `consumes`, default `application/json`); `in: formData` parameters → one `object`-schema `EndpointBodyOut` with each field as a property
- [x] 2.6 Implement 3.x response mapping: `responses[code].content[contentType].{schema,example}` → `EndpointResponseOut` per status code
- [x] 2.7 Implement 2.0 response mapping: `responses[code].schema` (no `content` wrapper) → `EndpointResponseOut`, content type from `produces` (default `application/json`)
- [x] 2.8 Ensure every schema value (parameter/body/response) that is or contains a bare `{"$ref": "..."}` is passed through verbatim into `EndpointSchemaOut`-shaped dicts — no `components`/`definitions` resolution
- [x] 2.9 Wrap per-operation mapping so one malformed operation is caught, logged (`logger.warning`, naming the API/method/path), and skipped without aborting the rest of the spec's parse

## 3. Upsert / lifecycle sync

- [x] 3.1 Implement `sync_endpoints_from_spec(details: ApiDetails) -> None` in `openapi_import.py`: no-op when `details.type != ApiDetails.TYPE_OPENAPI` or `details.spec_content` is empty
- [x] 3.2 Parse `spec_content` into the set of intermediate operation records (§2); on a spec-level parse failure (no recognizable version key, unusable `paths`), log, set `endpoints_sync_failed=True`, leave existing `ApiEndpoint` rows untouched, and return without raising
- [x] 3.3 For each parsed operation, upsert an `ApiEndpoint` keyed by `(api, method, path)`: create if absent (`status='active'`); if present and `active`, update changed fields only; if present and `removed`, update fields and revive to `active` (design.md Decision 2)
- [x] 3.4 After processing all parsed operations, set `status='removed'` on every existing `active` `ApiEndpoint` for this API whose `(method, path)` was not among them; never touch rows already `removed`, never delete any `ApiEndpoint` or `ServiceEndpointUsage` row
- [x] 3.5 On a fully successful sync, set `endpoints_synced_at=now()` and `endpoints_sync_failed=False` on `details` (caller persists via `update_fields` alongside its own save, or a dedicated `details.save(update_fields=[...])` — match whatever `signals.py`'s receiver does to avoid recursive `post_save` loops)
- [x] 3.6 Wrap the upsert pass (§3.3-3.4) in one DB transaction so a partial sync can't leave some endpoints updated and others stale if an unexpected error occurs mid-pass

## 4. Wiring into the existing write paths

- [x] 4.1 Add a `post_save` receiver on `ApiDetails` in `plugins/apis/backend/atlas_plugin_apis/signals.py` that calls `openapi_import.sync_endpoints_from_spec(instance)`, alongside the existing `_recompute_on_save`/`recompute_relations` receiver — do not modify `spec_fetch.py`, `kinds/api_handler.py`, or `atlas_plugin_ingestion.pipeline`/`due_for_spec_refresh` (design.md Decision 1: the signal is the single shared hook, not three call sites)
- [x] 4.2 Guard against signal re-entrancy: `sync_endpoints_from_spec`'s own `details.save(update_fields=[...])` for `endpoints_synced_at`/`endpoints_sync_failed` must not re-trigger a second full sync pass (e.g. save with `update_fields` limited to those two columns, and confirm the receiver doesn't loop — add a regression test in §7)
- [x] 4.3 Verify via test that creating an `openapi`-typed API with inline `spec_content` produces `ApiEndpoint` rows before the create request returns (`atlas_plugin_apis.api.views` path)
- [x] 4.4 Verify via test that `due_for_spec_refresh()` (`atlas_plugin_apis.extension_points`) produces/updates `ApiEndpoint` rows after a periodic refresh, with no changes needed to `due_for_spec_refresh` itself or to `atlas_plugin_ingestion`

## 5. API surface

- [x] 5.1 Add `endpoints_synced_at`/`endpoints_sync_failed` to `ApiSpecOut` (`api/schemas.py`) and populate them in `_api_out` (`api/views.py`) and `ApiKindHandler.serialize_details` (`kinds/api_handler.py`)
- [x] 5.2 Add both fields as read-only columns/fields on the `ApiDetails` Django admin (`admin.py`), matching how `spec_resolved_at`/`spec_resolve_failed` are already surfaced there (note: no `ApiDetails` admin existed prior to this change despite the task's premise — registered a new `ApiDetailsAdmin` covering both the pre-existing spec fields and the new sync fields, all read-only)

## 6. Frontend

- [x] 6.1 Add an "Endpoint sync failed" indicator (mirroring `ApiSpecPanel.tsx`'s existing `StaleSpecLabel`) shown on the API detail page when `endpointsSyncFailed` is true
- [x] 6.2 Resolve design.md's open question on distinguishing spec-derived vs. manually-authored endpoints in the UI (e.g. a small badge on the Endpoint list/detail page) — implement if in scope, or explicitly defer with a one-line note in this file if not (implemented: a page-level note on the Endpoints tab, and a "Source" field on the Endpoint Overview tab's Details card, both derived from `api.type === 'openapi' && api.specContent !== ''` — an *active* endpoint on such an API is always spec-derived per design.md Decision 2/6, so no per-endpoint flag/migration is needed)
- [x] 6.3 Update frontend API client types for the two new `ApiSpecOut` fields (note: the actual type — `ApiSpec` — lives in `core/frontend/src/lib/types.ts`, not `plugins/apis/frontend/src/lib`, which only holds this plugin's own `Endpoint`-related types; updated there plus the fixture/mock builders that construct a full `ApiSpec` literal)

## 7. Tests

- [x] 7.1 Parser unit tests: 3.x `requestBody`/responses, 2.0 `in: body`, 2.0 `in: formData` (multiple fields → one object schema), path/query/header parameters both versions, `in: cookie` dropped without failing the operation, `$ref` stored verbatim and unresolved
- [x] 7.2 Upsert unit tests: new operation creates; changed operation updates fields and preserves `id`; operation missing from re-parse soft-removes (and preserves `ServiceEndpointUsage`); `removed` operation reappearing revives with updated fields and preserved links
- [x] 7.3 Failure-path tests: spec with no recognizable version key sets `endpoints_sync_failed=True` and leaves existing endpoints untouched without raising; a spec with one malformed operation among valid ones imports the valid ones and skips only the bad one without setting `endpoints_sync_failed`; a later successful sync clears `endpoints_sync_failed` and updates `endpoints_synced_at`
- [x] 7.4 Integration tests: `POST /api/apis` with an inline OpenAPI spec produces endpoints synchronously; `PATCH /api/apis/{id}` with changed `spec_content` re-syncs; `due_for_spec_refresh()` re-syncs a URL-sourced API's endpoints; non-`openapi`-typed and empty-`spec_content` APIs are never synced
- [x] 7.5 Regression test confirming the `endpoints_synced_at`/`endpoints_sync_failed` self-save (§4.2) does not cause a second sync pass or infinite signal recursion
- [x] 7.6 Frontend test for the sync-failed indicator's visibility toggling on `endpointsSyncFailed`

**Fix discovered while adding 7.4's integration coverage:** wiring the importer into `ApiDetails`'s `post_save` signal (§4.1) made `seed_booking_demo.py`'s `_create_apis` step also trigger `sync_endpoints_from_spec` for every `openapi`-typed demo API, which then collided with `_create_endpoints`'s subsequent `ApiEndpoint.objects.create(...)` calls for the same `(api, method, path)` keys (`apiendpoint_unique_api_method_path` `IntegrityError`) — not just the content-drift risk design.md's Risks section anticipated, but an outright seed-command crash. Fixed by changing `_create_endpoints` to `ApiEndpoint.objects.update_or_create(...)` so the hand-authored demo text always wins over whatever the importer already wrote (`core/backend/server/apps/catalog/management/commands/seed_booking_demo.py`); also corrected `_template_endpoints`'s docstring, which claimed "this change ships no OpenAPI importer" (no longer true). Covered by the existing `test_seed_booking_demo.py` suite, which now passes again.

## 8. Validation

- [x] 8.1 Run this change's spec scenarios (`specs/openapi-endpoint-import/spec.md`, `specs/api-endpoints/spec.md`) against the implemented tests and confirm each scenario maps to at least one passing test (every `openapi-endpoint-import` scenario maps to a new test in `atlas_plugin_apis/tests/test_openapi_import.py` or `server/apps/catalog/tests/test_api_spec.py`; the `api-endpoints` scenarios unchanged by this change — "No create/edit endpoint exists", "Removed endpoint is still reachable", "warns about existing dependents", "cannot receive new links" — are still covered by their pre-existing tests from `add-endpoint-dependency-explorer`, all still passing; the two scenarios this change adds to that capability ("disappearing from a re-parsed spec is removed", "revives when the spec adds it back") map to the new upsert tests)
- [x] 8.2 `openspec validate --changes import-openapi-endpoints --strict` passes before archiving
