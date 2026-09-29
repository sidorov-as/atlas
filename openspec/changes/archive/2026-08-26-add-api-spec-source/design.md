## Context

`API.definition` is a single `TextField` that is either pasted spec text or a URL, with nothing recording which. The web UI renders it verbatim in a `<pre>` block for every API type. There is no file storage anywhere in this codebase, and CONTEXT.md records an explicit prior decision (ADR 0002, diagrams-on-demand) that object storage is unnecessary at this scale — that decision should not be silently reopened by this change. Ingestion runs as a single-process poll loop with no Celery/Redis (`apps/ingestion/management/commands/ingest.py`), which already tolerates and logs per-item failures without surfacing them anywhere but the server log (`apps/ingestion/pipeline.py`).

## Goals / Non-Goals

**Goals:**
- Make "is this a URL or pasted content" an explicit, machine-readable field instead of an implicit convention.
- Let an API's spec be resolved from a URL and kept reasonably fresh without introducing a task queue.
- Render OpenAPI/AsyncAPI specs as real documentation where a renderer exists, and degrade to a plain download everywhere else, including when rendering fails.
- Keep the model generic enough that adding a future spec kind (e.g. a JSON Schema or WSDL renderer) never requires backend changes — only a new `TYPE_CHOICES` entry and a frontend renderer registration.

**Non-Goals:**
- No object/blob storage. `spec_content` is a plain text column; file upload is a browser-side convenience that reads text into that column, never a stored binary.
- No server-side schema/format validation of spec content (no OpenAPI/AsyncAPI JSON-Schema validation, no YAML/JSON format detection). The renderer library is the only thing that ever parses `spec_content`.
- No task queue. Refresh reuses the existing single-process poll loop.
- No rendering for `grpc`/`graphql` in this change — they get the same download action every type gets, nothing more.
- No cross-entity reuse. This is API-only; other entity kinds are not touched.

## Decisions

**Explicit `spec_source` discriminator over "whichever field is non-empty".**
Two independent nullable fields (a `spec_url` and a `spec_content` with no discriminator) leaves "both are set" undefined. An explicit `none | inline | url` enum makes the active source unambiguous and is what the refresh job keys off (`spec_source == 'url'`).

**`spec_content` is always the resolved snapshot, never the source-of-record for a URL.**
Every consumer (renderer, download action) reads only `spec_content`. It doesn't matter to them whether that text arrived by paste, file upload, or fetch — `spec_url` is consulted only by the thing that refreshes `spec_content`. This is what keeps the model generic: nothing downstream needs source-specific branching.

**Server-side resolution and snapshotting (chosen over live client-side fetch of `spec_url`).**
Fetching `spec_url` directly from the browser on every tab-open is simpler to build but fails against any spec host without permissive CORS headers (internal wikis, auth-gated endpoints) and gives no offline/point-in-time copy. Resolving server-side, once on save and then periodically, mirrors the existing `catalog-info.yaml` ingestion model (fetch server-side, store a snapshot) and means the frontend never makes a cross-origin request.

**Refresh piggybacks on the existing ingestor poll loop rather than a new scheduler.**
`ingest.py` already runs `while True: run_ingestion_pass(); sleep(interval)` with no Celery/Redis, justified in its own docstring by the project's scale. A second pass function (`refresh_spec_urls`) added to the same loop needs no new process, dependency, or deployment change. It runs regardless of whether a given API is YAML-managed or manually created — `spec_source == 'url'` is the only filter, independent of `source_kind`.

**Skip-and-log on refresh failure, not a hard error, following `pipeline.py`'s existing convention.**
A failed fetch (network error, 404, or a response that doesn't look like text a spec renderer could plausibly consume — empty, or fails a YAML-or-JSON parse) leaves `spec_content` untouched and sets `spec_resolve_failed = True`. This is a deliberately cheap gate: it exists only to stop an error page from clobbering a good snapshot, not to validate that the content is a well-formed OpenAPI/AsyncAPI document. Successful resolution clears `spec_resolve_failed` and updates `spec_resolved_at`.

**The renderer is the validator; render failure and "no renderer for this type" share one fallback.**
Redoc and `@asyncapi/react-component` both parse raw YAML-or-JSON text themselves. Rather than duplicate that parsing server-side to decide whether content is "valid," the frontend attempts to render for `openapi`/`asyncapi` and catches failure; `grpc`/`graphql` never attempt rendering at all. Both cases land on the same "Download spec" action, so the UI has exactly one degraded state to design for, not two.

**Download action is universal, not type-gated.**
Originally scoped as "just a link" for the two unrendered types, but since it's also the render-failure fallback for the two rendered types, gating it by type would mean building it twice. Every API with non-empty `spec_content` shows it.

**Stale-fetch indicator reuses existing UI primitives (`Label` danger theme + `Tooltip`), not a new component.**
Both are already used elsewhere in this frontend (`TagLabels.tsx`, `railFields.tsx` for `Label`; `FlowGraph.tsx`, `FlowFormPage.tsx` for `Tooltip`). This is a deliberate departure from the rest of the ingestion pipeline's silent-log-only convention — spec staleness left unindicated for months was judged worse than a one-line label.

## Risks / Trade-offs

- **[Risk]** A `spec_url` behind auth or requiring headers Atlas doesn't send will always fail to resolve. → Out of scope for v1; it fails closed (stays on last-good `spec_content` or empty, flagged via `spec_resolve_failed`), not silently wrong.
- **[Risk]** No content-length/type cap on fetched or pasted `spec_content` could let a very large or non-text response bloat the database. → Add a practical size cap at write time (reject, don't truncate) rather than skip this entirely; exact limit is an implementation detail, not a spec-level concern.
- **[Trade-off]** Because there's no server-side parse/validate step, a garbage inline paste is only caught visually, when a human opens the Documentation tab and sees the fallback. Accepted: the alternative (per-type validation) is exactly the coupling this design avoids.
- **[Risk]** `refresh_spec_urls` runs every poll interval and does one HTTP fetch per URL-sourced API; at "a few hundred entities" scale (per `ingest.py`'s own stated assumption) this is negligible, but it does mean refresh cadence is tied to `INGESTOR_POLL_INTERVAL`, not independently configurable. → Acceptable for v1; split into its own interval only if that coupling becomes a real complaint.

## Migration Plan

- Django migration: add `spec_source`, `spec_url`, `spec_content`, `spec_resolved_at`, `spec_resolve_failed`; data-migrate existing rows to `spec_source='inline'`, `spec_content=definition`, then drop `definition`.
- Manifest schema (`ApiSpecIn`/`ApiSpecPatch`): `definition` replaced by `specSource`/`specUrl`/`specContent`; `specResolvedAt`/`specResolveFailed` are output-only (`ApiSpecOut`), never settable by a human or a manifest.
- No rollback complexity beyond a standard reverse migration; no external data is moved (nothing to reconcile with an object store, since there isn't one).

## Open Questions

- None outstanding — all prior open threads (resolution timing, validation philosophy, scope, staleness UI) were resolved during exploration.
