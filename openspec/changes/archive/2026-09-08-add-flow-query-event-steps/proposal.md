## Why

Flow's step grammar can only reference a registered Entity Kind via `entity_ref` (`kind:name`, resolved through core's `resolve_ref()`), but `ApiEndpoint`/`ApiOperation` (`atlas_plugin_apis`'s `api-endpoints`/`api-operations` capabilities) are deliberately **not** registered Entity Kinds — plugin-owned, UUID-addressed child rows of an `api` entity. A Flow documenting a cross-system process can today point at an API as a whole, but never at the specific endpoint or channel operation actually involved in a step — the most concrete, useful reference a Query/Event step could carry. `extract-flows-plugin` (archived 2026-09-08) named this explicitly as its motivating "unblocks": it moved Flow onto plugin footing precisely so it could reach `atlas_plugin_apis` through a declared `.extension_points` surface, the same inversion-of-control shape `atlas_plugin_ingestion`/`atlas_plugin_standard_catalog` already use. This change is that follow-up.

## What Changes

- Add two new, mutually exclusive Flow step fields — `query_ref` (an Endpoint reference) and `event_ref` (an Operation reference) — alongside the existing `entity_ref`/`external_label` pair. Each stores a point-in-time snapshot (the owning API ref, the endpoint/operation id, and display fields: `method`/`path` for a Query, `direction`/`channel` for an Event) rather than a live pointer — the canvas renders entirely from the step's own JSON today, with no fetch, and this preserves that.
- Extend `atlas_plugin_flows`'s `validate_steps()` to resolve a `query_ref`/`event_ref` through two new `atlas_plugin_apis.extension_points` functions (`resolve_endpoint`/`resolve_operation`), mirroring `due_for_spec_refresh()`'s existing shape. Guarded by `django_apps.is_installed('atlas_plugin_apis')` — a distribution without `atlas.apis` gets a clear validation error on such a step, not a crash. A `removed` endpoint/operation is a valid reference (Flow documents a process, not live API state); the check also confirms the endpoint/operation actually belongs to the referenced API.
- Add two new `atlas_plugin_apis` REST endpoints, `GET /api/apis/endpoints/search/` and `GET /api/apis/operations/search/`, searching across every API's active endpoints/operations by the same fields their existing per-API `search` filter already uses (`path`/`summary`/`operation_id` and `channel_address`/`summary`/`operation_id`), each result carrying its owning API's ref/name/title.
- Add Query (`Magnifier` icon, colored by HTTP method) and Event (`Bolt` icon, colored by direction) as two new node kinds/tiles in the Flow canvas and its "Add Step" picker, with a single flat search-as-you-type lookup (via the new endpoints above) rather than a two-stage "pick an API, then pick an endpoint" flow.
- Make the existing six entity-kind step pickers (`RefSelect`) filterable, matching the already-filterable `TargetRefSelect` in the same file — no backend change needed there.
- When `atlas.apis` isn't selected in the running distribution, the Query/Event tiles in the "Add Step" picker render disabled with an explanatory tooltip, detected via the existing `/healthz/plugins/` health endpoint (a deliberate, acknowledged reuse of an ops-monitoring endpoint for a UI capability check — no new cross-plugin frontend contract is introduced).
- **Non-Goal**: no live re-fetch of Endpoint/Operation data when the canvas renders — the stored snapshot can drift from the source after a spec re-import (acknowledged, asymmetric between Query and Event — see design.md); no generic cross-plugin frontend capability-detection mechanism; no change to `atlas.flows`'s manifest dependencies (`atlas.apis` stays a soft, optional integration, not a `requires_plugins` entry).

## Capabilities

### New Capabilities
- `flow-query-event-steps`: Flow step types Query and Event, each snapshotting a reference to an `atlas_plugin_apis` Endpoint/Operation, rendered on the canvas with a dedicated icon and CRUD/direction-based coloring.
- `api-endpoint-operation-search`: cross-API search of `ApiEndpoint`/`ApiOperation` records — a REST surface (`GET /api/apis/endpoints/search/`, `GET /api/apis/operations/search/`) and an `atlas_plugin_apis.extension_points` resolution surface (`resolve_endpoint`, `resolve_operation`) for other plugins.

### Modified Capabilities
- `flow-management`: a step's mutual-exclusion rule (today `entity_ref` vs. `external_label`) extends to a four-way exclusion including `query_ref`/`event_ref`; `validate_steps()` gains the resolution/ownership checks described above.
- `visual-flow-editor`: the "Add Step" node-type picker gains Query/Event tiles (disabled, with a tooltip, when `atlas.apis` is absent); the entity-kind lookup becomes filterable/searchable.

## Impact

- **Backend**: `atlas_plugin_flows` (`models.py`'s `validate_steps()`, step shape validation); `atlas_plugin_apis` (two new search controllers/serializers, two new `extension_points` functions).
- **Frontend**: `@atlas/plugin-flows` (`flowNodeKind.ts`, a new palette/badge module, `FlowStepModal.tsx`, `FlowNodes.tsx`, `flowSteps.ts`/`flowStepSchema.ts`, a new thin `endpointsApi`/`operationsApi` REST client — no npm dependency on `@atlas/plugin-apis`, which the existing `importBoundary.test.ts` forbids); `core/frontend`'s `RefSelect.tsx` (adds `filterable`).
- **No manifest/dependency change**: `atlas.flows` keeps its existing `requires_plugins={'atlas.standard-catalog': ...}` only; the `atlas.apis` integration stays soft/optional, guarded at both the backend (`is_installed`) and frontend (`/healthz/plugins/`) layers.
- **No database migration beyond the two plugins' existing `steps`/endpoint-search JSON shapes** — `Flow.steps` is already a schemaless `JSONField`; no new Django model is introduced.
