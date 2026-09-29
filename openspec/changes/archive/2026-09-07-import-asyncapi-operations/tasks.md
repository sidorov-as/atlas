## 1. Data model

- [x] 1.1 Add `ApiDetails.operations_synced_at` (nullable `DateTimeField`) and `ApiDetails.operations_sync_failed` (`BooleanField`, default `False`) to `plugins/apis/backend/atlas_plugin_apis/models/api.py`
- [x] 1.2 Generate and check in the new Django migration (purely additive; no changes to `ApiOperation`/`ServiceOperationUsage`)

## 2. AsyncAPI parser (`asyncapi_import.py`)

- [x] 2.1 Create `plugins/apis/backend/atlas_plugin_apis/asyncapi_import.py`; add a version detector that loads `spec_content` via `yaml.safe_load` and returns which of `asyncapi: "2.x"` / `asyncapi: "3.x"` / neither it is
- [x] 2.2 Implement the 2.x `channels` walker: one intermediate operation record per channel's `publish` and/or `subscribe` field, mapping `direction` per design.md Decision (2.x `publish` → `receive`, `subscribe` → `send`) and `operation_key` to `channel_address + direction`
- [x] 2.3 Implement the 3.0 `operations` walker: one intermediate operation record per `operations` map entry, resolving its referenced `channel` for `channel_address`, mapping `direction` from `action` unchanged, and `operation_key` to the operations-map key
- [x] 2.4 Implement `channel_protocol` resolution: 2.x resolves only when the document's top-level `servers` map has exactly one entry; 3.0 resolves only when a channel's `servers` list references exactly one server; otherwise left empty (design.md Decision 4)
- [x] 2.5 Implement message mapping common to both versions: `payload` → schema (verbatim, `$ref` unresolved), first `examples[]` entry's `payload` → example, `operationId`/`title`, `summary`, `description`, `tags` (Tag Object `name`s) → the matching `ApiOperation` fields
- [x] 2.6 Implement `oneOf` message handling: one `ApiOperation.message` entry per alternative (design.md Decision 5)
- [x] 2.7 Implement the 3.0 name-only fallback for a `messages` entry that is a bare unresolved `$ref` with no inline payload (Non-Goals: no `components`/message-map resolution)
- [x] 2.8 Wrap per-channel/per-operation mapping so one malformed entry is caught, logged (`logger.warning`, naming the API/channel/operation), and skipped without aborting the rest of the spec's parse

## 3. Upsert / lifecycle sync

- [x] 3.1 Implement `sync_operations_from_spec(details: ApiDetails) -> None` in `asyncapi_import.py`: no-op when `details.type != ApiDetails.TYPE_ASYNCAPI` or `details.spec_content` is empty
- [x] 3.2 Parse `spec_content` into the set of intermediate operation records (§2); on a spec-level parse failure (no recognizable version key, unusable `channels`), log, set `operations_sync_failed=True`, leave existing `ApiOperation` rows untouched, and return without raising
- [x] 3.3 For each parsed operation, upsert an `ApiOperation` keyed by `operation_key` (scoped to the API): create if absent (`status='active'`); if present and `active`, update changed fields only; if present and `removed`, update fields and revive to `active`
- [x] 3.4 After processing all parsed operations, set `status='removed'` on every existing `active` `ApiOperation` for this API whose `operation_key` was not among them; never touch rows already `removed`, never delete any `ApiOperation` or `ServiceOperationUsage` row
- [x] 3.5 On a fully successful sync, set `operations_synced_at=now()` and `operations_sync_failed=False` on `details`, saved via `update_fields` (mirroring `openapi_import.sync_endpoints_from_spec`'s own save shape, to work with §4.2's guard)
- [x] 3.6 Wrap the upsert pass (§3.3-3.4) in one DB transaction so a partial sync can't leave some operations updated and others stale if an unexpected error occurs mid-pass

## 4. Wiring into the existing write paths

- [x] 4.1 Add a `post_save` receiver on `ApiDetails` in `plugins/apis/backend/atlas_plugin_apis/signals.py` (`_sync_operations_on_save`) that calls `asyncapi_import.sync_operations_from_spec(instance)`, alongside the existing `_recompute_on_save`/`_sync_endpoints_on_save` receivers — do not modify `spec_fetch.py`, `kinds/api_handler.py`, or `atlas_plugin_ingestion.pipeline`/`due_for_spec_refresh` (design.md Decision 1)
- [x] 4.2 Expand `signals.py`'s `_SYNC_STATUS_FIELDS` frozenset to include `operations_synced_at`/`operations_sync_failed` alongside the existing two OpenAPI fields, and use that expanded set as the early-return guard in **both** `_sync_endpoints_on_save` and `_sync_operations_on_save` (design.md Decision 2); add a regression test confirming neither receiver's own status self-save triggers a second full sync pass from either receiver
- [x] 4.3 Verify via test that creating an `asyncapi`-typed API with inline `spec_content` produces `ApiOperation` rows before the create request returns
- [x] 4.4 Verify via test that `due_for_spec_refresh()` produces/updates `ApiOperation` rows for an `asyncapi`-typed API after a periodic refresh, with no changes needed to `due_for_spec_refresh` itself

## 5. API surface

- [x] 5.1 Add `operations_synced_at`/`operations_sync_failed` to `ApiSpecOut` (`api/schemas.py`) and populate them in `_api_out` (`api/views.py`) and `ApiKindHandler.serialize_details` (`kinds/api_handler.py`), alongside the existing `endpoints_synced_at`/`endpoints_sync_failed` fields
- [x] 5.2 Add both fields as read-only columns/fields on the `ApiDetails` Django admin (`admin.py`), matching how `endpoints_synced_at`/`endpoints_sync_failed` are already surfaced there

## 6. Seed data — consolidate to one source of truth (design.md Decision 6)

- [x] 6.1 Fix `ASYNCAPI_SPEC`'s `booking.confirmed` and `payout.completed` channels to use `publish` instead of `subscribe`, and `notification.delivery-status` to use `subscribe` instead of `publish` — no change needed to `BOOKING_EVENTS_ASYNCAPI_SPEC`'s single channel, which already agrees
- [x] 6.2 Enrich both demo specs so they carry everything `OPERATIONS` used to add on top: each operation's `description` and `tags` (2.x Tag Objects), each message's `name`, and each channel's embedded `payload.example` moved into a proper message-level `examples: [{payload: {...}}]` field (so §2.5's mapping populates `.example`) — content equivalent to what `OPERATIONS` currently asserts for the same channels
- [x] 6.3 Delete `OPERATIONS` and `_create_operations()`; replace `_create_operations()`'s call site with a lookup step that queries the `ApiOperation` rows already written by `sync_operations_from_spec` (triggered synchronously inside `_create_apis()`'s loop via `ApiDetails.post_save`) into the `{(api, operation_key): ApiOperation}` dict `_create_operation_usages()` needs — no upsert, just a read of what the importer already produced
- [x] 6.4 Run `seed_booking_demo` end-to-end and confirm the resulting `ApiOperation` rows have the same `operation_key`s `OPERATION_USAGES` references (`payout.completed-receive`, `notification.delivery-status-send`, `booking.confirmed-send`) and equivalent documentation content to before this change, with no duplicate/orphaned rows per channel

## 7. Frontend

- [x] 7.1 Add an "Operation sync failed" indicator (mirroring `ApiSpecPanel.tsx`'s existing `EndpointSyncFailedLabel`/`StaleSpecLabel`) shown on the API detail page when `operationsSyncFailed` is true
- [x] 7.2 Update frontend API client types for the two new `ApiSpecOut` fields (`core/frontend/src/lib/types.ts`'s `ApiSpec`, plus fixture/mock builders that construct a full `ApiSpec` literal)

## 8. Tests

- [x] 8.1 Parser unit tests: 2.x `publish`/`subscribe` direction mapping, 3.0 `action` passthrough, 2.x/3.0 `operation_key` derivation, `channel_protocol` resolution (single server, multiple servers, 3.0 per-channel `servers` reference), message `payload`/`examples` mapping, `oneOf` multi-message, `$ref` stored verbatim, 3.0 bare-`$ref` message name-only fallback
- [x] 8.2 Upsert unit tests: new operation creates; changed operation updates fields and preserves `id`; operation missing from re-parse soft-removes (and preserves `ServiceOperationUsage`); `removed` operation reappearing revives with updated fields and preserved links
- [x] 8.3 Failure-path tests: spec with no recognizable version key sets `operations_sync_failed=True` and leaves existing operations untouched without raising; a spec with one malformed channel among valid ones imports the valid ones and skips only the bad one without setting `operations_sync_failed`; a later successful sync clears `operations_sync_failed` and updates `operations_synced_at`
- [x] 8.4 Integration tests: creating an `asyncapi`-typed API with an inline spec produces operations synchronously; patching with changed `spec_content` re-syncs; `due_for_spec_refresh()` re-syncs a URL-sourced API's operations; non-`asyncapi`-typed and empty-`spec_content` APIs are never synced
- [x] 8.5 Regression test confirming the `operations_synced_at`/`operations_sync_failed` self-save (§4.2) does not cause a second sync pass or infinite signal recursion, in either direction between the two sync receivers
- [x] 8.6 Frontend test for the operation-sync-failed indicator's visibility toggling on `operationsSyncFailed`
- [x] 8.7 `server.apps.catalog.tests.test_seed_booking_demo` (or equivalent): running `seed_booking_demo` produces the expected `ApiOperation` row count (no duplicates), the specific `operation_key`s `OPERATION_USAGES` depends on exist, and `_create_operation_usages()`'s lookup step succeeds against importer-produced rows

## 9. Validation

- [x] 9.1 Run this change's spec scenarios (`specs/asyncapi-operation-import/spec.md`, `specs/api-operations/spec.md`) against the implemented tests and confirm each scenario maps to at least one passing test
- [x] 9.2 `openspec validate --changes import-asyncapi-operations --strict` passes before archiving
