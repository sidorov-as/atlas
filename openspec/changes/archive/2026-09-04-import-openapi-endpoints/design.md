## Context

`atlas_plugin_apis` today has two independent write paths for `ApiDetails`, and both already converge on shared functions rather than duplicating logic:

```
User creates/patches API           Ingestor's periodic poll loop
        │                                   │
        ▼                                   ▼
ApiKindHandler.create_details/    atlas_plugin_apis.extension_points
update_details (kinds/api_handler.py)   .due_for_spec_refresh()
        │                                   │
        ▼                                   ▼
spec_fetch.apply_api_spec_source()   spec_fetch.resolve_api_spec_url()
        │  (calls resolve_api_spec_url            │
        │   when spec_source == 'url')            │
        └───────────────┬──────────────────────────┘
                         ▼
              details.save(...)  ──► post_save signal
                         │
                         ▼
              signals.py: _recompute_on_save(instance)
                         │
                         ▼
              recompute_relations(instance.entity)
```

Two things follow from this shape:

1. `apply_api_spec_source` is **not** the single shared choke point — the periodic-refresh path calls `resolve_api_spec_url` directly and never goes through `apply_api_spec_source` (it doesn't need to; `spec_source` is already `url` and doesn't change). The one function every `ApiDetails` write actually passes through, regardless of path, is `details.save(...)`, which is why `signals.py` already hangs `recompute_relations` off `post_save` instead of calling it from each write site.
2. `ApiEndpoint`/`ServiceEndpointUsage` (`add-endpoint-dependency-explorer`) already exist and are already designed to be import-compatible: `ApiEndpoint.id` is its own UUID never derived from `method`/`path`, uniqueness is `(api, method, path)`, and removal is soft (`status='removed'`) specifically so a future importer could "notice it disappeared from a spec" (design.md of that change, Decision 7) without invalidating existing `ServiceEndpointUsage` rows. No schema change to `ApiEndpoint` is needed for this change — only a producer for it.

This change adds that producer: an OpenAPI parser plus an upsert routine, triggered the same way `recompute_relations` already is — off `ApiDetails`'s `post_save` signal — so every write path gets it for free.

## Goals / Non-Goals

**Goals:**
- Parse `spec_content` for an `openapi`-typed API (OpenAPI 3.x and Swagger 2.0) into the exact `ApiEndpoint`/`request`/`responses` shapes `api/schemas.py` already defines and the frontend already renders.
- Run identically after every successful spec resolution — first save, later PATCH, and periodic `spec_url` refresh — via one hook, not three call sites remembering to invoke a function.
- Upsert by `(api, method, path)`: create new, update changed, revive a previously-removed operation that reappears, and soft-remove (never delete) an operation that disappears — preserving every existing `ServiceEndpointUsage` row regardless of which of those four things happens to its endpoint.
- Fail safe: a spec that can't be parsed as OpenAPI never raises out of a save/refresh request and never mutates existing `ApiEndpoint` rows; the failure is recorded and surfaced the same way `spec_resolve_failed` already is.

**Non-Goals (deferred to a later change):**
- Resolving `$ref` (e.g. `#/components/schemas/Foo`) into its referenced schema. Stored verbatim, matching what `EndpointSchemaOut.ref`/`EndpointSchemaViewer.tsx` already do with an unresolved `$ref` string (they render its last path segment as a label, nothing more) — resolving it would require walking `components`/`definitions`, handling circular refs, and changing a frontend contract that already works today for zero product benefit this change needs.
- Path-parameter normalization (`{id}` vs `{userId}`) — inherited as-is from `add-endpoint-dependency-explorer` design.md Decision 4; exact-string `path` remains the identity.
- Any self-service "re-import now" button, import history/audit log, or diff preview UI. Sync is implicit in saving/refreshing the spec, same as `spec_content` resolution itself.
- Reconciling `seed_booking_demo.py`'s hand-authored `_template_endpoints()` with this importer's actual output — noted as a risk below, not fixed here.
- `asyncapi`/`grpc`/`graphql`-typed APIs. `ApiEndpoint` is method+path shaped; only `type='openapi'` is in scope, matching the existing seed-data precedent ("seeds Endpoints for every `openapi`-typed demo API").

## Decisions

### 1. Hook into `ApiDetails`'s existing `post_save` signal, not into `apply_api_spec_source`
**Decision:** Add a second `post_save` receiver in `signals.py` (or extend `_recompute_on_save`) that calls `openapi_import.sync_endpoints_from_spec(instance)`. This fires after every `details.save()`, regardless of which of the three write paths produced it.

**Why:** As the Context section shows, `apply_api_spec_source` isn't actually shared by the periodic-refresh path — only `post_save` is. Hooking there is also exactly the precedent `signals.py`'s own docstring states for `recompute_relations`: "every way an entity's kind-specific data can be written... recomputes relations the same way without every call site needing to remember to do it." Endpoint sync has the identical requirement, so it gets the identical mechanism.

**Alternative considered:** Call `sync_endpoints_from_spec` explicitly from inside `apply_api_spec_source` and add a second explicit call inside `due_for_spec_refresh`. Rejected: two call sites for one behavior, one of which (`due_for_spec_refresh`) would need to remember to add it — the same duplication `recompute_relations` already avoids by using a signal.

**Consequence:** the sync runs on *every* `ApiDetails` save, including ones where `spec_content` didn't change (e.g. only `type`/`system` was patched). This is intentionally cheap and idempotent by construction (Decision 2's upsert only writes rows whose fields actually differ), so a no-op parse-and-diff on an unrelated metadata edit is wasted CPU, not wasted writes. Acceptable given `ApiDetails` write volume; revisit only if profiling shows otherwise.

### 2. Upsert by `(api, method, path)`, four possible outcomes per parsed operation
**Decision:** For each operation the parser extracts, look up an existing `ApiEndpoint` by `(api, method, path)`:
- **Not found** → create it, `status='active'`.
- **Found, `status='active'`, fields differ** → update the differing fields in place (id and any `ServiceEndpointUsage` links are untouched — they FK the row, not its content).
- **Found, `status='active'`, fields identical** → no write.
- **Found, `status='removed'`** → revive: update fields and set `status='active'`.

After processing every parsed operation, any existing `ApiEndpoint` for this `api` with `status='active'` whose `(method, path)` was **not** among the parsed operations is set to `status='removed'`. Rows already `status='removed'` and still absent are left alone (no-op). No `ApiEndpoint` row is ever deleted by this path, and `ServiceEndpointUsage` is never touched by it directly — matching `add-endpoint-dependency-explorer`'s existing soft-delete invariant exactly, just with the importer as a second trigger alongside the existing admin action.

**Why revive on reappearance:** the alternative — leaving a reappeared operation `removed` until an admin manually un-removes it — has no mechanism to un-remove today (Decision 7 of the prior change shipped no such admin action, only "Mark as removed") and would silently defeat the entire point of a live-synced spec: an endpoint that was briefly missing from a spec (e.g. a bad deploy) would stay invisible forever after the spec is fixed. Reviving is the behavior a spec-driven source of truth implies.

**Alternative considered:** Diff by content hash of the whole spec to skip parsing entirely when `spec_content` is byte-identical to last sync. Rejected for this change: requires storing a hash, and the per-field upsert (this decision) is already a no-op write-wise when nothing changed — the only thing a hash would save is the parse itself, which is not expensive enough at expected spec sizes (tens to low hundreds of operations) to justify the extra persisted state. Revisit if real-world specs prove larger than expected.

### 3. Parser is a hand-rolled walker over the already-`yaml.safe_load`-parsed dict, not a new OpenAPI library dependency
**Decision:** `openapi_import.py` parses `yaml.safe_load(spec_content)` (JSON is valid YAML, so one loader handles both) into a plain `dict`, detects version via top-level `openapi: "3.x"` vs `swagger: "2.0"`, and walks `paths` → per-method operation objects directly, translating each into the `ApiEndpoint` field shapes. No new dependency is added to `pyproject.toml` (currently only `pyyaml`/`requests` beyond the framework).

**Why:** `EndpointSchemaOut`'s own docstring already establishes the precedent this plugin follows: "a provisional, JSON-Schema-*like* type descriptor... not a JSON Schema implementation," covering exactly six primitive shapes plus `$ref`/`enum`/`nullable`. A general OpenAPI object-model library (`openapi-spec-validator`, `prance`, etc.) is built to fully validate and often to resolve `$ref`s across `components`/`definitions` — machinery this change explicitly doesn't want (Non-Goals) and that would need reconciling across both 2.0 and 3.x object models. A ~150-line walker producing exactly the six fields `api/schemas.py` already contracts for is simpler, has no new supply-chain surface, and can't drift from the read models' expectations since it's written directly against them.

**Alternative considered:** Add `openapi-spec-validator` (or similar) for validation, keep a hand-rolled walker for extraction. Rejected: adds a dependency whose main value (schema validation against the OpenAPI meta-schema) this change doesn't need — a spec that's *invalid* OpenAPI but still has a recognizable `paths` structure should still import what it can, not be rejected wholesale; "deliberately cheap gate, not spec validation" is already `spec_fetch.py`'s stated philosophy for the layer below this one, and this layer inherits it.

### 4. Normalizing 2.0 and 3.x into one shape
**Decision:** Both versions produce the same `request`/`responses` dicts (`api/schemas.py`'s `EndpointRequestOut`/`EndpointResponseOut` shapes):
- **Parameters** (`in: path|query|header`, both versions use the same `in`/`name`/`required` keys): mapped 1:1. `in: cookie` (3.x only) is dropped — `EndpointParameterLocation` has no `cookie` variant; dropping one parameter doesn't fail the whole operation.
- **Request body:** 3.x `requestBody.content[contentType].{schema,example}` maps directly. 2.0's `in: body` parameter (whose `schema` *is* the body schema) and separately-modeled `in: formData` parameters are both translated into the same `request.body` shape (`formData` becomes an inferred `object` schema with each form field as a property) — 2.0 has no explicit content type for `body`, so `application/json` is assumed unless `consumes` says otherwise.
- **Responses:** 3.x `responses[code].content[contentType].{schema,example}` maps directly. 2.0 `responses[code].schema` (no `content` wrapper) maps to the same shape with content type from `produces` (default `application/json`) and no separate `example` key in 2.0 (2.0 uses `examples`, an out-of-scope niche; left empty when absent).

**Why:** This is the minimum translation needed to make both versions land on one shape without special-casing every consumer of `ApiEndpoint.request`/`.responses` by spec version — the read models (`EndpointRequestOut`/`EndpointResponseOut`) and every frontend component built against them already assume one shape (`add-endpoint-dependency-explorer`), and that contract shouldn't change for this import concern.

**Alternative considered:** Support 3.x only, reject 2.0 specs outright (treat as a parse failure). Rejected: Swagger 2.0 specs are still common in the wild (`ApiDetails.type` doesn't distinguish OpenAPI major version, and nothing today validates which version a pasted/fetched spec actually is), and the cost of supporting both is a handful of extra mapping branches, not a second parser.

### 5. Parse/sync failures never raise out of the save path; surfaced via new `ApiDetails` fields, mirroring `spec_resolve_failed`
**Decision:** `sync_endpoints_from_spec` catches every exception internally (`yaml.safe_load` failure — shouldn't happen since `spec_fetch` already validated this on resolve, but content can still fail to look like a recognizable `paths` structure — missing/malformed `paths`, neither `openapi` nor `swagger` version key present, an individual operation that doesn't map cleanly). On failure: log via `logger.exception` (matching `due_for_spec_refresh`'s existing per-API catch-and-continue style), leave every existing `ApiEndpoint` row for this API untouched, and set two new fields on `ApiDetails`:
- `endpoints_synced_at: DateTimeField(null=True, blank=True)` — set on every successful sync (mirrors `spec_resolved_at`).
- `endpoints_sync_failed: BooleanField(default=False)` — set `True` on failure, `False` on the next success (mirrors `spec_resolve_failed`).

A single malformed *operation* inside an otherwise-parseable spec (e.g. one path item with a nonsensical `parameters` block) is caught per-operation, not per-spec: that one operation is skipped (logged) and the rest of the spec still imports — a single bad operation shouldn't blank out an entire API's endpoint list.

**Why:** `api-spec-documents`'s "Stale spec indicator" requirement already established the UI pattern for "the last attempt to derive fresher data from this API failed, here's the last-good snapshot, don't hide that it's stale" — endpoint sync failing is the same shape of problem one layer up (spec_content resolved fine, but this plugin couldn't derive endpoints from it), so it gets the same signal instead of a new, different one.

**Alternative considered:** Silently log and swap nothing user-visible (matching `due_for_spec_refresh`'s current per-API exception handling, which has no persisted-failure field at all). Rejected: that already exists for one layer (fetch) and un-mirrored failure visibility between two adjacent layers (fetch vs. parse) would be a confusing asymmetry — a user staring at zero endpoints for a spec they know has `paths` in it needs *some* signal that it's a parse problem, not "nobody's gotten around to authoring endpoints yet."

### 6. Manual admin edits to an importer-managed endpoint are overwritten on next sync — documented, not prevented
**Decision:** No "manually overridden, don't resync this field" flag is introduced. For an `openapi`-typed API, every successful sync treats the spec as the source of truth for every field it can populate (`summary`, `description`, `deprecated`, `tags`, `request`, `responses`, `operation_id`) — a Django-admin edit to one of those fields on an importer-managed endpoint survives only until the next successful sync.

**Why:** Introducing a per-field or per-endpoint "locked" flag is real complexity (schema, admin UI, and a merge rule for every future field) for a scenario this change has no evidence is a real workflow yet — nothing today lets anyone hand-edit an `openapi`-typed API's endpoints except Django admin, which is an operator escape hatch, not a supported authoring path once import exists. `add-endpoint-dependency-explorer`'s own design.md already scoped manual authoring as a stopgap ("a future change... is the natural path to self-service authoring" — this change *is* that future change, for `openapi`-typed APIs specifically).

**Alternative considered:** Skip re-syncing fields that differ from what the last sync wrote (i.e., treat any admin-made diff as an intentional override). Rejected: needs a stored "last synced value" per field to detect an admin override at all, which is exactly the extra state being avoided, for a workflow (mixing spec-derived and hand-edited fields on the same endpoint) nobody has asked for.

## Risks / Trade-offs

- **[Risk]** Decision 6 means an admin's manual correction to a spec-derived endpoint doesn't stick. → **Mitigation:** documented explicitly here and should be called out in the `endpoint.edit`-adjacent admin UI copy (out of this change's scope to design the exact copy, but the risk is on record); the real fix is fixing the *spec*, which is the actual source of truth once import is live.
- **[Risk]** `seed_booking_demo.py`'s `_template_endpoints()` docs are hand-authored to match `openapi_spec()`'s template text "by construction," not by parsing (`add-endpoint-dependency-explorer` design.md's own Open Questions note). Once this importer exists, running it against that same template text may produce a *different* result than the hand-authored docs (e.g. a `deprecated` or `removed` endpoint the template hand-crafts but the generated spec text doesn't actually mark deprecated/absent) — a future reader could reasonably expect the two to match and be surprised they don't. → **Mitigation:** not fixed in this change (Non-Goal); flagged here so it isn't mistaken for an importer bug when noticed. Reconciling seed data with real import output is a natural follow-up, not required for this change to be correct.
- **[Risk]** A very large spec (thousands of operations) parsed synchronously inside a `post_save` signal could make an API's create/patch request or one iteration of the periodic refresh loop noticeably slower. → **Mitigation:** none needed at expected scale (the existing seed data tops out at a few dozen operations per API); if a real deployment hits this, the fix is moving the sync off the synchronous save path entirely (e.g. a task queue), which is a bigger change than this one and not warranted without evidence.
- **[Risk]** A spec that validly represents an operation this parser doesn't recognize (e.g. an exotic `parameters` shape, OpenAPI 3.1's JSON-Schema-dialect body schemas) silently skips that one operation rather than erroring loudly per-operation. → **Mitigation:** every skip is logged (`logger.warning`, operation-level, not swallowed silently in the sense of "no trace anywhere") — accepted as this change's design (Decision 5's "one bad operation doesn't blank the API"), revisit if silent per-operation skips prove hard to notice in practice.

## Migration Plan

- One new Django migration in `atlas_plugin_apis` adding `ApiDetails.endpoints_synced_at` (nullable datetime) and `ApiDetails.endpoints_sync_failed` (boolean, default `False`) — purely additive, no change to `ApiEndpoint`/`ServiceEndpointUsage`'s existing schema (`add-endpoint-dependency-explorer`'s tables are reused as-is).
- No backfill: on deploy, every existing `openapi`-typed API with a non-empty `spec_content` gets endpoints on its *next* save or periodic refresh, not immediately — the periodic refresh loop (`due_for_spec_refresh`) reaches every `spec_source='url'` API on its existing schedule regardless, so URL-sourced specs backfill themselves within one refresh cycle; `spec_source='inline'` APIs whose content hasn't changed since before this change won't re-sync until their next manual edit (their `post_save` doesn't fire without a write). Note this as an expected, one-time gap rather than building a one-off backfill management command for it — acceptable since inline specs are the less common source in the seeded/demo data.
- Rollback: reverse the one migration (drop the two new columns); `ApiEndpoint`/`ServiceEndpointUsage` rows already created by the importer are ordinary rows indistinguishable from admin-authored ones and are **not** removed by rollback — same as every other plugin migration in this codebase, this is a data-affecting rollback only in the sense that future syncs stop happening, not that past sync output is undone.

## Open Questions

- Should an `inline`-sourced `openapi`-typed API's endpoints backfill on deploy via a one-off management command, or is "re-syncs on next manual edit" (Migration Plan) acceptable? Leaning toward accepting the gap (matches this document's Migration Plan) — confirm during implementation if the seeded/demo data makes the gap visible in a way that looks like a bug.
- Should the Endpoints list (or an individual Endpoint's page) visibly distinguish "spec-derived" from "manually authored" endpoints, given Decision 6's overwrite behavior? Proposal.md flags this as an open frontend question; leaning toward yes (a small "Imported from spec" vs. no badge) but not blocking this design — resolve during task planning.
