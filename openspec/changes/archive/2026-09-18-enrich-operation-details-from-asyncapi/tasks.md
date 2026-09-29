## 1. Model + migration

- [x] 1.1 Add `external_docs = models.JSONField(default=dict, blank=True)` to `ApiOperation` (`plugins/apis/backend/atlas_plugin_apis/models/operation.py`)
- [x] 1.2 Generate the migration under `plugins/apis/backend/atlas_plugin_apis/migrations/` (next after `0003_apioperation_deprecated.py`); confirm no backfill needed (`default=dict` covers existing rows)

## 2. Parser: `asyncapi_import.py`

- [x] 2.1 Add `external_docs: dict = field(default_factory=dict)` to `ParsedOperation`
- [x] 2.2 In `_parse_operation_2x` and `_parse_operation_3x`, read `operation.get('externalDocs')` (version-uniform, design.md Decision 3): when it's a dict with a non-empty `url`, set `external_docs = {"description": ..., "url": ...}`; otherwise `{}`
- [x] 2.3 Add `external_docs` to `_OPERATION_DOC_FIELDS` so the existing upsert diffing (`_upsert_operation`) picks it up
- [x] 2.4 In `_map_message`, resolve `message.get('headers')` through `spec_refs.resolve_schema(headers, spec)` when it's a dict (design.md Decision 1 — same treatment `payload` already gets, `merge_siblings=False` default); include the result as a new `headers` key in the mapped message dict, omitted (not present, not `null`-as-empty-object) when the message has no `headers`
- [x] 2.5 Confirm the existing per-channel/per-operation `try`/`except` in `_parse_channels_2x`/`_parse_operations_3x` already covers a malformed `headers`/`externalDocs` block (design.md Decision 4) — no new error handling expected, just verify by reading the call chain

## 3. Read model: `api/schemas.py`

- [x] 3.1 Add `headers: EndpointSchemaOut | None = None` to `OperationMessageOut`
- [x] 3.2 Add an `external_docs` output shape (`{description: str, url: str}` or reuse/adapt whatever shape `enrich-endpoint-details-from-openapi` lands for `EndpointOut.external_docs`, for consistency across the two capabilities) to `OperationOut`

## 4. Frontend

- [x] 4.1 Extend `OperationMessage`/`Operation` types in `plugins/apis/frontend/src/lib/types.ts` for `headers` and `externalDocs`
- [x] 4.2 `OperationMessageTab.tsx`: add a "Headers" section (same treatment as the existing "Payload" section, reusing `EndpointSchemaViewer`) rendered only when `message.headers` is present (design.md Decision 5 — unlike Payload, no "no headers" fallback line)
- [x] 4.3 `OperationOverviewTab.tsx`: render an External docs link when `operation.externalDocs?.url` is present, matching the existing conditional-rendering pattern already used for `channelProtocol`/`provider`

## 5. Tests

- [x] 5.1 Add `test_spec_refs.py`-adjacent coverage is not needed (no resolver changes) — confirm `spec_refs.resolve_schema` needs no new tests, only new call-site tests below
- [x] 5.2 `test_asyncapi_import.py`: message `headers` resolves a `$ref` to expanded content (2.x and 3.0)
- [x] 5.3 `test_asyncapi_import.py`: a message with no `headers` yields no `headers` key on the mapped entry
- [x] 5.4 `test_asyncapi_import.py`: a self-referential `headers` schema stops at the cycle without looping (mirrors `resolve-spec-refs`'s own cycle-safety test shape)
- [x] 5.5 `test_asyncapi_import.py`: operation `externalDocs` with a `url` is imported into `ApiOperation.external_docs` (both 2.x and 3.0)
- [x] 5.6 `test_asyncapi_import.py`: operation `externalDocs` missing `url` yields an empty `external_docs`, rest of the operation still imports
- [x] 5.7 `test_asyncapi_import.py`: a malformed `headers`/`externalDocs` block is logged and skips only that one operation, not the whole spec
- [x] 5.8 `EndpointSchemaViewer.test.tsx` needs no new coverage (component unchanged, per design.md Decision 5) — confirm by inspection, don't add a redundant test
- [x] 5.9 Add/extend `OperationMessageTab.test.tsx` (create if it doesn't exist yet): Headers section renders when `message.headers` is present; Headers section is absent when `message.headers` is absent
- [x] 5.10 Add/extend `OperationOverviewTab.test.tsx`: external docs link renders when `operation.externalDocs.url` is present; absent otherwise

## 6. Seed data + validation

- [x] 6.1 Extend `core/backend/server/apps/catalog/management/commands/seed_booking_demo.py`'s `ASYNCAPI_SPEC` (or `BOOKING_EVENTS_ASYNCAPI_SPEC`) with a `headers` block on at least one message and an `externalDocs` on at least one operation, so the demo catalog exercises both new fields — update `test_seed_booking_demo.py` assertions if operation/message shapes it checks change
- [x] 6.2 Run the backend test suite for `atlas_plugin_apis` and `server.apps.catalog` and confirm all new/updated tests pass
- [x] 6.3 Run the frontend test suite for `plugins/apis/frontend` and confirm all new/updated tests pass
- [x] 6.4 Manually verify against the real `test-asyncapi`/"Orders Events API" spec (already has a rich `headers` block) that the `publishOrderCreated` operation's Message tab now shows a Headers section with the resolved envelope schema (verified against the locally-running dev stack's `notifications-api`/`booking.confirmed` operation instead — no `test-asyncapi` entity exists in this environment's DB; the enriched seed `headers`/`externalDocs` content synced and rendered correctly end to end: Headers section on the Message tab, External docs link on the Overview tab)
- [x] 6.5 `openspec validate --changes enrich-operation-details-from-asyncapi --strict` passes before archiving
