## Why

`API.definition` is a single untyped `TextField` documented as "Inline spec text or a link," with nothing distinguishing which one a given value actually is. The web UI can't act on that ambiguity, so it just dumps the raw string into a `<pre>` block on every API's Overview tab — OpenAPI and AsyncAPI specs render as unformatted text instead of the interactive documentation those formats support, and there's no way to point at a spec by URL and have Atlas keep a working copy.

## What Changes

- Replace `API.definition` with an explicit, source-typed representation: `spec_source` (`none` / `inline` / `url`), `spec_url`, `spec_content` (the resolved, always-current snapshot regardless of source), `spec_resolved_at`, and `spec_resolve_failed`. **BREAKING**: `definition` is removed from the API create/update/patch schemas and from `catalog-info.yaml` manifests; existing data is migrated (`spec_source='inline'`, `spec_content=definition`) rather than dropped.
- Saving an API with `spec_source='url'` fetches `spec_url` once, synchronously, to populate `spec_content`.
- The ingestor's existing poll loop gains a second pass that periodically re-fetches `spec_url` for every API with `spec_source='url'`, overwriting `spec_content` only when the response is non-empty and parses as YAML-or-JSON; a fetch that fails or looks implausible leaves the last-good `spec_content` in place and sets `spec_resolve_failed`, logged and skipped the same way the rest of the ingestion pipeline already handles per-item failures.
- No format or schema validation of `spec_content` is performed server-side, for any spec kind. The API detail page renders `spec_content` through a type-specific renderer when one exists (OpenAPI via Redoc, AsyncAPI via `@asyncapi/react-component`) and treats a render failure as "no renderer available" — falling back to the same raw-download affordance used for types without a renderer at all.
- API detail page: a "Documentation" tab appears only for `openapi`/`asyncapi` types and renders `spec_content` (falling back to a download link if rendering fails). A "Download spec" action is available for every API type regardless of `spec_source` or whether it has a renderer.
- API detail page: when `spec_resolve_failed` is true, a `Label` (danger theme) with an explanatory tooltip appears near the spec affordances, indicating `spec_content` is a stale last-good copy.
- API form page: replace the single `definition` textarea with a source picker (paste text / provide a URL / upload a file — a file upload just reads the file's text client-side into the same inline-content field, no new storage mechanism).

## Capabilities

### New Capabilities
- `api-spec-documents`: The API entity's spec-source model (inline / url / none), server-side URL resolution and periodic refresh with stale-on-failure semantics, and type-conditional rendering/download on the API detail page.

### Modified Capabilities
- `catalog-web-ui`: The existing "Resource or API detail shows only Overview and Relations" scenario no longer holds for API — API detail pages gain a conditional Documentation tab and a Download-spec action; Resource is unaffected.

## Impact

- **Backend**: `apps/catalog/models/api.py` (field replacement + migration), `apps/catalog/api/schemas.py` (`ApiSpecIn`/`ApiSpecPatch`/`ApiSpecOut`), `apps/catalog/api/views.py` (create/update field wiring, synchronous first-fetch on `spec_source='url'`), `apps/ingestion/upsert.py` (manifest field wiring), `apps/ingestion/pipeline.py` (new `refresh_spec_urls` pass), `apps/ingestion/management/commands/ingest.py` (call the new pass each loop iteration).
- **Frontend**: `pages/ApiDetailPage.tsx` (Documentation tab, download action, stale-fetch label), `pages/ApiFormPage.tsx` (source picker replacing the textarea), `lib/railFields.tsx` or equivalent (stale-fetch `Label`). New dependencies: `redoc` (or equivalent OpenAPI viewer) and `@asyncapi/react-component`.
- **catalog-info.yaml manifests**: `spec.definition` is replaced by `spec.specSource`/`spec.specUrl`/`spec.specContent` — a breaking manifest schema change for any repository currently declaring an API's `definition`.
- **No new infrastructure**: no object storage, no Celery/Redis — the refresh job reuses the existing single-process poll loop.
