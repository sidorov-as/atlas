## Context

`extract-flows-plugin` (archived 2026-09-08) moved `Flow` out of `server.apps.catalog` into `atlas_plugin_flows` for one explicit reason: a plugin can call into another plugin's declared `.extension_points`/`.contracts` surface (the shape `atlas_plugin_ingestion` and `atlas_plugin_standard_catalog` already use against `atlas_plugin_apis`), while core code reaching into an optional plugin cannot. That change did no more than clear the ground — "no new Flow step kinds, no reference to `atlas_plugin_apis` or its `ApiEndpoint`/`ApiOperation` models" was its explicit Non-Goal. This change is the follow-up it named.

The core obstacle: `ApiEndpoint`/`ApiOperation` are deliberately *not* registered Entity Kinds (`api-endpoints`/`api-operations` specs: "SHALL NOT be a registered Entity Kind") — they are plugin-owned child rows of an `api` `CatalogEntity`, addressed by their own UUID primary key, not by a `kind:name` ref. Flow's existing `entity_ref` grammar is resolved through `atlas_plugin_api.refs.resolve_ref()`, which only understands registered kinds (`KIND_CHOICES`). It cannot, and structurally should not, be taught about a plugin-owned non-entity child row — that would either add an `atlas_plugin_apis`-specific case to a core-owned resolver (breaking the layering the whole extraction program protects) or promote Endpoint/Operation to real Entity Kinds (rejected by their own specs). A parallel, plugin-owned addressing path is required.

A second constraint shapes the frontend half of this change: `core/frontend/src/plugins/importBoundary.test.ts` already enforces that no first-party frontend plugin package imports another's directly ("only `@atlas/plugin-api` is a shared cross-plugin dependency"). Whatever `@atlas/plugin-flows` needs from `atlas_plugin_apis`'s Endpoint/Operation data, it must reach over REST, the same way the backend reaches it through `.extension_points` rather than a direct model import.

## Goals / Non-Goals

**Goals:**
- A Flow step can reference a specific `ApiEndpoint` (Query) or `ApiOperation` (Event), rendered on the canvas with a distinct icon and CRUD/direction-based color, matching how Endpoints already color HTTP methods.
- `atlas.flows` stays optional and independent of `atlas.apis`'s selection — a distribution can select Flow without Apis (as today), and a distribution with both degrades a specific Query/Event *authoring* affordance, not the whole plugin, when Apis is absent.
- The canvas keeps rendering directly from the persisted `steps` JSON with no network fetch at render time (existing `FlowNodes.tsx`/`flowNodeKindOf()` behavior, unchanged for every other node kind).
- `validate_steps()` stays a pure validator — it checks a step's references resolve; it never rewrites or "heals" what a client submitted.

**Non-Goals:**
- No live re-fetch of Endpoint/Operation data when the canvas renders a Query/Event node — see Decision 2's accepted staleness trade-off.
- No new `atlas.flows` → `atlas.apis` manifest dependency (`requires_plugins`) — the integration stays the same soft, optional shape `atlas_plugin_ingestion` already uses against `atlas_plugin_apis`.
- No generic, reusable "is plugin X selected" capability API for the frontend — Decision 4 deliberately reuses an existing ops endpoint instead of building one, scoped to this one need.
- No change to `api-endpoints`/`api-operations`'s own requirements (Endpoint/Operation stay non-entity child resources) — this change only adds a *search* surface alongside them.

## Decisions

### Decision 1 — `query_ref`/`event_ref` are new step fields, not an extension of `entity_ref`'s grammar

A step's `entity_ref` is a `[kind:][namespace/]name` string resolved by core's `resolve_ref()`. Reusing that channel for an Endpoint/Operation would require either a fake, non-registered "kind" prefix that `resolve_ref()` special-cases (coupling core to `atlas_plugin_apis`, exactly what the extraction avoided) or a second parser living outside `refs.py` that happens to share its string shape (confusing — one string grammar, two silently different resolution paths). Instead, two new, optional, mutually exclusive fields are added alongside the existing `entity_ref`/`external_label` pair:

```json
"query_ref": { "api": "api:orders-api", "endpoint": "<uuid>", "method": "GET", "path": "/orders/{id}" }
"event_ref": { "api": "api:orders-api", "operation": "<uuid>", "direction": "send", "channel": "orders.created" }
```

`api` is a normal `kind:name` ref (`api` *is* a registered kind, resolved by the existing `resolve_ref(ref, expected_kind='api')` unchanged) — it is carried for human legibility in the hand-editable JSON/Monaco editor and as a cheap ownership cross-check (Decision 3), even though `endpoint`/`operation` alone (a globally unique UUID primary key, not scoped by API) would technically be sufficient to resolve the row.

A step's mutual-exclusion rule generalizes from a pair to a four-way check: at most one of `entity_ref`, `external_label`, `query_ref`, `event_ref` may be present.

Rejected: a single unified `api_ref: { type: 'endpoint' | 'operation', ... }` field — two named fields read more directly off `flowNodeKindOf()`'s existing per-field-presence dispatch (mirrors how `external_label`'s mere presence already selects the External kind) and need no extra `type` discriminant.

### Decision 2 — Snapshot, not a live pointer; the staleness risk is asymmetric between Query and Event, and is accepted

`FlowNodes.tsx` renders every node type today from the step's own JSON, with zero network calls — an entity-backed node's subtitle is `refName(entity_ref)`, parsed from the ref string itself. Making Query/Event nodes the first kind that requires a fetch to render would be a real architectural break, and would mean a Query/Event node simply fails to render meaningfully in a distribution where `atlas.apis` has since been removed, even though the rest of the Flow is unaffected. So `query_ref`/`event_ref` snapshot their display fields (`method`/`path`, `direction`/`channel`) at the moment they're picked, written by the frontend picker, never recomputed by the server.

This is **not a uniform risk**:
- **Query is safe by construction.** `openapi_import.py::_upsert_operation` uses `(method, path)` as the upsert identity for `ApiEndpoint` — a spec re-import that changes either field creates a *new* `ApiEndpoint` row and soft-removes the old one (`status=removed`); it never mutates `method`/`path` on an existing row's id. A `query_ref` snapshot therefore cannot drift from its own referenced row.
- **Event can drift.** `asyncapi_import.py::_upsert_operation`'s identity is `operation_key` alone; `direction` and `channel_address` are ordinary `_OPERATION_DOC_FIELDS` the importer freely overwrites on every re-sync of the *same* row. An `event_ref` snapshot's `direction`/`channel` can therefore silently disagree with the operation's current state after a spec re-import.

Accepted as-is: building a re-sync mechanism (e.g., re-deriving the snapshot from the live row on every Flow save) would turn `validate_steps()` from a pure validator into something that mutates step content — a bigger, more invasive change for a narrower payoff, and inconsistent with `title`/`summary` already being free-text fields nobody keeps in sync with anything. Flagged here explicitly so it isn't silently forgotten: an Event node's color/label can go stale in a way a Query node's cannot.

Rejected: live-fetch at render time (breaks the offline-canvas invariant, and makes a Query/Event node's rendering depend on `atlas.apis` still being installed even for an unrelated Flow edit); server-side re-derivation of the snapshot on every save (turns a pure validator into a mutator, for a risk already judged acceptable).

### Decision 3 — Validation: resolve, cross-check ownership, tolerate `removed`, never mutate

`atlas_plugin_flows.models.validate_steps()` (extended alongside its existing `_validate_step_shape`) does the following for a `query_ref`/`event_ref`, in order:

1. Shape-check the field (a dict with exactly the expected keys/types).
2. Resolve `api` via the existing `resolve_ref(ref, expected_kind='api')` — no new core code.
3. Resolve `endpoint`/`operation` via two new `atlas_plugin_apis.extension_points` functions, `resolve_endpoint(id)`/`resolve_operation(id)`, mirroring `due_for_spec_refresh()`'s existing shape in the same module. Guarded by `django_apps.is_installed('atlas_plugin_apis')` *before* the import — an absent `atlas.apis` raises a `StepValidationError` with a clear message, not an `ImportError`. This copies `atlas_plugin_standard_catalog.kinds.__init__._register_api_delete_guard`'s guard pattern deliberately, not `atlas_plugin_ingestion.pipeline`'s unconditional top-level `from atlas_plugin_apis.extension_points import due_for_spec_refresh` — that import has no such guard today, an existing gap this change does not repeat.
4. Cross-check that the resolved endpoint/operation's owning API matches the resolved `api` entity (`endpoint.api_id == api_entity.id`) — catches a mismatched pair (e.g., a UUID copied from the wrong API's endpoint list).
5. A `removed` endpoint/operation is accepted, not rejected — Flow documents a process, and `ServiceEndpointUsage`/`ServiceOperationUsage` already tolerate a `removed` reference for the same reason (their own model docstrings: never cascade-deleted when the endpoint/operation goes away, only when the owning API entity itself is deleted). Rejecting `removed` here would make an already-saved Flow un-editable the moment the API it documents evolves.

`validate_steps()` does not rewrite `method`/`path`/`direction`/`channel` from the resolved row — see Decision 2.

### Decision 4 — Frontend optionality: reuse `/healthz/plugins/`, not a new capability API

No frontend plugin can today learn whether another optional plugin is selected in the running distribution: `core/frontend/src/plugins/composition.ts` is composer-generated and only imported by core, and `importBoundary.test.ts` forbids a plugin importing another's package (which would be the natural place to smuggle such a signal through anyway). Building a proper, generic "plugin capability" surface for this is a materially bigger change than this one warrants for a single UI affordance.

Instead, `FlowStepModal` calls the already-existing, unauthenticated `GET /healthz/plugins/` (`runtime-failure-isolation` spec, `server/health.py::PluginHealthView`) on mount, and looks for `{"id": "atlas.apis", "status": "active"}` in its `plugins` array. If absent or not `active`, the Query/Event tiles render `disabled` with a tooltip ("Requires the APIs plugin") rather than being hidden — a deliberate choice so the option's existence stays discoverable even where it can't be used yet.

This is a conscious semantic reuse: `/healthz/plugins/` exists for ops monitoring/runtime-failure-isolation, not UI feature-detection, and this is the first place it's read for the latter. If it ever becomes auth-gated or changes shape for monitoring reasons, this is the one frontend call site that would need to follow. Accepted rather than building a dedicated capability endpoint, because the alternative is new backend *and* frontend contract surface for a single, narrow, cosmetic disabled-state check.

Rejected: always showing the tiles enabled and letting the picker fail empty/erroring (worse UX, no signal to the author about *why*); building a purpose-made "plugin capabilities" REST/contract surface (disproportionate to this one need).

### Decision 5 — Endpoint/Operation search is a new global route in `atlas_plugin_apis`, not a client-side merge

The "Add Step" picker for Query/Event needs a single flat, search-as-you-type lookup across every API's endpoints/operations — closer to a command-palette than the two-stage "pick an API, then pick an Endpoint" flow the REST API's existing `apis/<api_id>/endpoints/` shape would otherwise force. Two ways to get there were weighed:

- **Client-side merge** (fetch every `api` entity, fan out one `endpointsApi.list(apiId)` call per API, merge and filter in the browser) — matches the codebase's existing idiom exactly (`RefSelect`/`TargetRefSelect` already fetch-all-then-filter, uncapped past `pageSize: 100`), and needs no backend change at all.
- **A new global search route** — `GET /api/apis/endpoints/search/?q=...`, `GET /api/apis/operations/search/?q=...` in `atlas_plugin_apis`, reusing the exact `Q(...)` search fields its existing per-API `search` filter already applies (`path`/`summary`/`operation_id` for endpoints; `channel_address`/`summary`/`operation_id` for operations — `plugins/apis/backend/atlas_plugin_apis/api/views.py`), each result carrying `select_related('api')`'s ref/name/title for the picker's secondary line. Filtered to `status='active'` by default — a `removed` endpoint remains a valid *existing* reference (Decision 3) but shouldn't be offered when authoring a *new* one.

Chosen: the new global search route. It costs one small, self-contained addition to a plugin that already owns this data and already has the exact search-field precedent to copy, and it avoids an unbounded fan-out of one HTTP request per catalogued API every time an author opens "Add Step" — a cost the client-merge path would pay on every open, growing linearly with the size of the API catalog, for a picker that exists specifically to make Query/Event *pleasant* to author.

Rejected: client-side merge (chosen against, despite matching existing precedent, specifically because it doesn't scale with catalog size — the one thing the new UX is meant to fix); a single core-owned aggregator endpoint spanning both `CatalogEntity` kinds and plugin-owned Endpoint/Operation rows (would require core to depend on an optional plugin's data — exactly the antipattern `extract-flows-plugin` exists to avoid).

The existing six entity-kind pickers (`RefSelect`) are handled separately and more simply: they just gain `filterable: true`, matching `TargetRefSelect`'s already-established client-side-filter pattern in the same file — no backend change, since their full lists are already fetched up front today.

### Decision 6 — Frontend reaches `atlas_plugin_apis`'s data only over REST

`@atlas/plugin-flows` adds its own thin `endpointsApi.search()`/`operationsApi.search()` client (a few lines each, mirroring `plugins/apis/frontend/src/lib/entities.ts`'s existing shape) rather than depending on `@atlas/plugin-apis` as an npm package. This isn't a style preference — `importBoundary.test.ts` already asserts no first-party frontend plugin imports another's package directly, so a direct import would fail CI. REST is the only legal cross-plugin channel on the frontend, symmetric to `.extension_points` being the only legal one on the backend (Decision 3).

## Risks / Trade-offs

- **[Event snapshot staleness — Decision 2]** An `event_ref`'s `direction`/`channel` can silently disagree with the live `ApiOperation` after a spec re-import, since only `operation_key` is that model's upsert identity. → Mitigation: none built; accepted. A future change could add a "stale" visual hint by comparing snapshot to live state at *read* time only (no canvas fetch required for every node, just an optional detail-view check) if this proves to matter in practice.
- **[`/healthz/plugins/` semantic overload — Decision 4]** Reusing an ops health-check endpoint as a UI capability signal couples Flow's authoring UX to a monitoring surface's shape/availability. → Mitigation: isolate the call behind one small helper in `@atlas/plugin-flows` so a future dedicated capability endpoint (if ever built for other reasons) is a one-file swap.
- **[Removed-endpoint tolerance could surprise a Flow author]** Accepting `removed` references (Decision 3) means a newly-*edited* Flow can still validate against an endpoint the API author considers gone. → Mitigation: the search picker excludes `removed` results when *adding* a new step, so this can only happen to a reference that already existed; matches `ServiceEndpointUsage`'s precedent exactly.
- **[Two plugins change together]** Unlike most prior Flow work, this change touches `atlas_plugin_apis` (new search routes/extension points) as well as `atlas_plugin_flows` — a distribution/version-skew mismatch between the two plugin versions could leave `atlas_plugin_flows` calling `extension_points.resolve_endpoint`/`resolve_operation` functions an older `atlas_plugin_apis` doesn't yet export. → Mitigation: none beyond the ordinary plugin-version-range mechanism already in place for every other cross-plugin `.extension_points` call; not a new class of risk this change introduces.

## Migration Plan

1. `atlas_plugin_apis`: add `resolve_endpoint(id)`/`resolve_operation(id)` to `extension_points.py`; add the two search controllers/serializers/routes, defaulting to `status='active'`.
2. `atlas_plugin_flows`: extend `_validate_step_shape()`/`validate_steps()` per Decision 3 (shape check, `api` resolve, guarded `extension_points` resolve, ownership cross-check, four-way mutual exclusion).
3. `@atlas/plugin-flows` frontend: add `query`/`event` to `FlowNodeKind` (`flowNodeKind.ts`), their icons (`Magnifier`/`Bolt`) and color lookups (`METHOD_THEME`/`DIRECTION_THEME`, duplicated locally per `flowNodePalette.ts`'s existing precedent); extend `FlowNodes.tsx`'s subtitle rendering; extend `flowSteps.ts`/`flowStepSchema.ts`'s JSON parser/validator to mirror the backend's new fields and four-way exclusion; add the new search-tile UI and the `/healthz/plugins/`-driven disabled state to `FlowStepModal.tsx`.
4. `core/frontend`: add `filterable` to `RefSelect`.
5. Verify: existing `flow-management`/`visual-flow-editor` spec-scenario suites still pass unmodified for every pre-existing step kind; new scenarios (below) pass for Query/Event; a distribution without `atlas.apis` still composes and its Flow pages still work for every non-Query/Event step kind, with Query/Event tiles disabled.

Rollback: steps 1-4 are independently revertible code additions — no data migration, no schema change to `Flow.steps` (already a schemaless `JSONField`), no manifest/`requires_plugins` change to roll back.

## Open Questions

- Exact response shape/pagination limit for the two new search endpoints (e.g., `limit` param default/max) — mechanical, resolved during implementation, not a design blocker.
- Whether a future change should add a lightweight "this Event step's snapshot may be stale" indicator (Decision 2's Risk) — explicitly deferred, not part of this change.
