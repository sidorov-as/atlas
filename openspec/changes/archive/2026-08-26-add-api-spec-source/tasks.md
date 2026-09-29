## 1. Data model and migration

- [x] 1.1 Add `spec_source` (`none`/`inline`/`url`), `spec_url`, `spec_content`, `spec_resolved_at`, `spec_resolve_failed` fields to `API` in `apps/catalog/models/api.py`
- [x] 1.2 Write the migration: add the new fields, data-migrate existing rows (`spec_source='inline'`, `spec_content=definition` where `definition` is non-empty, else `spec_source='none'`), then drop `definition`
- [x] 1.3 Update `admin.py` if it references `definition`

## 2. API schemas and CRUD

- [x] 2.1 Replace `definition` with `spec_source`/`spec_url`/`spec_content` in `ApiSpecIn` and `ApiSpecPatch`; add `spec_resolved_at`/`spec_resolve_failed` as output-only fields on `ApiSpecOut` (`apps/catalog/api/schemas.py`)
- [x] 2.2 Update `apps/catalog/api/views.py` create/update/patch handlers to read/write the new fields instead of `definition`
- [x] 2.3 On create/update where `spec_source == 'url'`, synchronously fetch `spec_url` and populate `spec_content`/`spec_resolved_at`/`spec_resolve_failed`
- [x] 2.4 On create/update where `spec_source` is `none` or `inline`, clear/leave `spec_url`/`spec_resolved_at`/`spec_resolve_failed` as appropriate

## 3. Ingestion

- [x] 3.1 Update `apps/ingestion/upsert.py` to set the new fields (instead of `definition`) from manifest data
- [x] 3.2 Update `catalog-info.yaml` manifest schema usage (`ApiSpecIn` via `apps/ingestion/validation.py`) — confirm manifests can declare `specSource`/`specUrl`/`specContent`
- [x] 3.3 Add `refresh_spec_urls()` to `apps/ingestion/pipeline.py`: for every API with `spec_source == 'url'`, fetch `spec_url`; on non-empty response that parses as YAML-or-JSON, overwrite `spec_content`, set `spec_resolved_at`, clear `spec_resolve_failed`; on failure/empty/unparseable response, leave `spec_content` untouched, set `spec_resolve_failed = True`, log and continue to the next API
- [x] 3.4 Call `refresh_spec_urls()` from the poll loop in `apps/ingestion/management/commands/ingest.py`, alongside `run_ingestion_pass()`

## 4. Frontend — API form

- [x] 4.1 Replace the single `definition` `TextArea` in `pages/ApiFormPage.tsx` with a source picker: paste text, provide a URL, or upload a file
- [x] 4.2 Wire file upload to read the file's text client-side and populate the same inline-content field (`spec_source='inline'`, `spec_content=<file text>`) — no new upload endpoint or storage
- [x] 4.3 Update the create/update payload to send `specSource`/`specUrl`/`specContent` instead of `definition`

## 5. Frontend — API detail page

- [x] 5.1 Update `pages/ApiDetailPage.tsx` Overview tab to stop rendering raw `definition`/`spec_content` as a `<pre>` dump
- [x] 5.2 Add `redoc` (or equivalent read-only OpenAPI viewer) and `@asyncapi/react-component` as frontend dependencies
- [x] 5.3 Add a conditional "Documentation" tab for `type in (openapi, asyncapi)` that renders `spec_content` via the matching viewer, catching render failure and falling back to the download action
- [x] 5.4 Add a "Download spec" action, shown whenever `spec_content` is non-empty, for every API type
- [x] 5.5 Add a danger-themed `Label` wrapped in a `Tooltip` (matching existing usage in `TagLabels.tsx`/`railFields.tsx` and `FlowGraph.tsx`/`FlowFormPage.tsx`) shown when `spec_resolve_failed` is true, explaining the content is a stale last-good copy

## 6. Tests

- [x] 6.1 Backend: model/migration test covering the `definition` → `spec_source`/`spec_content` data migration
- [x] 6.2 Backend: CRUD tests for creating/updating an API with each `spec_source` value, including synchronous URL resolution on save
- [x] 6.3 Backend: `refresh_spec_urls` tests — successful refresh updates content and clears the failure flag; failed/empty/unparseable fetch preserves prior content and sets the failure flag; one failing API doesn't block refresh of others
- [x] 6.4 Backend: ingestion test — manifest declaring `specSource: url` / `specSource: inline` is ingested correctly
- [x] 6.5 Frontend: API detail page shows Documentation tab only for `openapi`/`asyncapi`; shows download action for all types with content; shows the stale-fetch label when `spec_resolve_failed` is true
