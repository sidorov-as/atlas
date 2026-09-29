## Why

Flow was left behind when the plugin-extraction program moved System/Component/Resource/API/C4/Ingestion out of core (`introduce-frontend-extension-points` design.md named Flows explicitly as one of the modules a later change would split out — it never got one). Today it still lives in `server.apps.catalog` and `frontend/src/plugins/core/`, which blocks a concrete, wanted follow-up: adding "Query" (from `atlas_plugin_apis`' `ApiEndpoint`) and "Event" (from `ApiOperation`) as new, live-referenceable Flow step kinds, with icons and CRUD-style coloring matching Endpoints' existing method badges. A core module cannot depend on an optional plugin's data without violating the enforced import-boundary rule (`core/backend/server/apps/plugins/tests/test_import_boundaries.py`); a plugin can, through the `.contracts`/`.extension_points` pattern `atlas_plugin_ingestion` and `atlas_plugin_standard_catalog` already use against `atlas_plugin_apis`. This change puts Flow on that footing. It changes no user-facing behavior by itself.

## What Changes

- Create `plugins/flows/` (backend Django app `atlas_plugin_flows` + frontend workspace package `@atlas/plugin-flows`), matching the shape of `plugins/apis/`, `plugins/standard-catalog/`, `plugins/c4/`, `plugins/ingestion/`.
- Move the `Flow` model, `validate_steps()`/`StepValidationError`, the Flow REST endpoints (list/detail create/patch/delete controllers), and their serializers/schemas out of `server.apps.catalog`/`server.apps.catalog.api` into the new plugin.
- Move Flow's frontend code — `FlowsListPage`/`FlowFormPage`/`FlowDetailPage`, `FlowCanvasEditor`/`FlowGraph`/`FlowNodes`/`FlowEdges`/`FlowTransitionModal`/`FlowStepModal`, `flowLayout.ts`/`flowNodeKind.ts`/`flowDiagramPreferences.ts`/`monacoFlowTheme.ts`/`flowSteps.ts` — out of `core/frontend/src/{pages,components,lib}` into `@atlas/plugin-flows`, and its route/nav-item contributions out of `frontend/src/plugins/core/{routes,navItems}.ts`.
- Register a new `atlas.flows.flow.edit`/`atlas.flows.flow.read` permission pair via `register_permission()`, replacing the direct `EntityWritePermission.check_create`/`check_write` calls Flow's views use today (core-internal, not published) — routed through the already-published `get_policy_evaluator().check(principal, permission, resource)`, checked against the Flow's `system` (an existing `CatalogEntity`) as `resource`, preserving today's exact ownership rule (member of `system.owner` may write) with no change to `RBACPolicyEvaluator` itself.
- Declare `atlas.flows` as an **optional** plugin (like `atlas.apis`/`atlas.c4`, not required like `atlas.standard-catalog`) with a manifest dependency on `atlas.standard-catalog` (Flow's `system` field resolves a System entity, mirroring `atlas.apis`' own dependency).
- Add `atlas_plugin_flows.plugin` to `SELECTED_PLUGINS` (`core/backend/server/settings/selected_plugins.py`) and the corresponding distribution manifest/lock source.
- Confirm `server.apps.catalog`/`frontend/src/plugins/core/` contain no remaining Flow-specific code.
- **BREAKING (internal)**: package/import paths for Flow's backend and frontend code move; no REST route, response shape, or UI behavior changes.
- **Non-Goal (explicit)**: no new Flow step kinds, no reference to `atlas_plugin_apis` or its `ApiEndpoint`/`ApiOperation` models, no icon/color work for Query/Event. This change only makes that follow-up possible; it does not implement it.

## Capabilities

### New Capabilities
- `flows-plugin`: Flow (the hand-authored cross-system process documentation feature) is provided by one optional first-party plugin, depending on `atlas.standard-catalog`, with no special core privileges beyond what any other plugin has access to.

### Modified Capabilities
- None — `flow-management` and `visual-flow-editor` behavior is unchanged; this is a pure code-location/packaging change validated by their existing spec-scenario suites continuing to pass unmodified.

## Impact

- **Backend**: new `plugins/flows/backend/` package; `server.apps.catalog` loses `models/flow.py` and its Flow API surface; `server.apps.catalog.api.permissions.EntityWritePermission`'s Flow call sites are replaced by a registered permission pair; `SELECTED_PLUGINS` gains `atlas_plugin_flows.plugin`, optional.
- **Frontend**: new `plugins/flows/frontend/` workspace package; `frontend/src/plugins/core/` loses its Flow routes/nav items; `core/frontend/src/{pages,components,lib}` lose their Flow-specific files.
- **Database**: `Flow`'s table and its existing rows are preserved — the Python model class moves, its `Meta.app_label` stays `'catalog'` (same migration-history-preserving technique `ApiDetails` used in `extract-apis-plugin`), no data migration needed.
- **Unblocks**: a follow-up change (not part of this one) that adds `atlas_plugin_apis.extension_points` entries for Endpoint/Operation ref resolution and lets `atlas_plugin_flows` call them for the new Query/Event step kinds — the motivating reason for doing this extraction now.
