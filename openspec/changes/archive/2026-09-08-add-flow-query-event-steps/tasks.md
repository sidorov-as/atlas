## 1. `atlas_plugin_apis`: cross-API search

- [x] 1.1 Add `ApiEndpointSearchController`/`ApiOperationSearchController` (or equivalent) to `plugins/apis/backend/atlas_plugin_apis/api/views.py`, reusing the existing per-API search `Q(...)` clauses verbatim (`path`/`summary`/`operation_id` for endpoints at ~views.py:288-292; `channel_address`/`summary`/`operation_id` for operations at ~views.py:384-388), scoped across every API (`select_related('api')`, no `api_id` filter), defaulting to `status='active'`.
- [x] 1.2 Add response serializers/schemas including each result's owning API's `ref`/`name`/`title`.
- [x] 1.3 Register `apis/endpoints/search/` and `apis/operations/search/` routes in `plugins/apis/backend/atlas_plugin_apis/api/urls.py`.
- [x] 1.4 Add backend tests: matches across multiple APIs, matches on each of the three search fields, `removed` excluded by default, response includes owning API's ref/name/title (endpoints and operations).

## 2. `atlas_plugin_apis`: extension_points resolution

- [x] 2.1 Add `resolve_endpoint(id)`/`resolve_operation(id)` to `plugins/apis/backend/atlas_plugin_apis/extension_points.py`, mirroring `due_for_spec_refresh()`'s existing shape (returns the row including its owning API, or a not-found result).
- [x] 2.2 Add tests: resolving an existing id, resolving a nonexistent id (no unhandled exception).

## 3. `atlas_plugin_flows`: step grammar and validation

- [x] 3.1 Extend `_validate_step_shape()`/`validate_steps()` in `plugins/flows/backend/atlas_plugin_flows/models.py`: shape-check `query_ref`/`event_ref` (required keys/types); four-way mutual exclusion across `entity_ref`/`external_label`/`query_ref`/`event_ref`.
- [x] 3.2 Resolve `query_ref.api`/`event_ref.api` via the existing `resolve_ref(ref, expected_kind='api')`.
- [x] 3.3 Resolve `query_ref.endpoint`/`event_ref.operation` via `atlas_plugin_apis.extension_points.resolve_endpoint`/`.resolve_operation`, guarded by `django_apps.is_installed('atlas_plugin_apis')` before the import — raise `StepValidationError` with a clear message when absent, not an `ImportError`.
- [x] 3.4 Cross-check the resolved Endpoint/Operation's owning API matches the resolved `api` entity; reject on mismatch.
- [x] 3.5 Confirm a `removed` Endpoint/Operation resolves successfully (no special-casing needed beyond not filtering by status in the resolver).
- [x] 3.6 Add/port backend tests for every scenario in `specs/flow-query-event-steps/spec.md`: resolvable query_ref/event_ref saves, unresolvable endpoint rejected, ownership-mismatch rejected, removed endpoint/operation still saves, four-way mutual exclusion, atlas.apis-absent rejection with a clear message (guard test can disable the app via Django app-registry mocking, matching the existing `is_installed` guard test pattern used for `_register_api_delete_guard`).

## 4. `@atlas/plugin-flows`: node kind, icons, colors

- [x] 4.1 Add `'query'`/`'event'` to `FlowNodeKind` in `plugins/flows/frontend/src/lib/flowNodeKind.ts`; extend `flowNodeKindOf()` to check `step.query_ref`/`step.event_ref` before the `entity_ref` prefix check.
- [x] 4.2 Add `Magnifier`/`Bolt` (from `@gravity-ui/icons`) to `FLOW_NODE_KIND_ICONS`, and `'Query'`/`'Event'` to `FLOW_NODE_KIND_LABELS`. (`@gravity-ui/icons` has no `Bolt` export — used `Thunderbolt`, its closest match.)
- [x] 4.3 Add a method/direction color lookup for Query/Event (a local `METHOD_THEME`/`DIRECTION_THEME`-equivalent, duplicated from `plugins/apis/frontend/src/lib/badges.ts` per `flowNodePalette.ts`'s existing precedent for fixed design constants) and wire it into node rendering in `FlowNodes.tsx` alongside the existing `FLOW_NODE_PALETTE`.
- [x] 4.4 Extend `FlowNodes.tsx`'s subtitle rendering: Query shows `${method} ${path}` from the snapshot, Event shows its snapshotted `channel` (optionally with `direction`) — no fetch.

## 5. `@atlas/plugin-flows`: search clients

- [x] 5.1 Add a thin `endpointsApi.search(query)`/`operationsApi.search(query)` REST client inside `@atlas/plugin-flows` (mirroring `plugins/apis/frontend/src/lib/entities.ts`'s shape), calling the new `apis/endpoints/search/`/`apis/operations/search/` routes — no dependency on `@atlas/plugin-apis` (forbidden by `core/frontend/src/plugins/importBoundary.test.ts`).
- [x] 5.2 Add a `/healthz/plugins/` client call (a small helper) that checks whether `atlas.apis` is present with `status: 'active'`.

## 6. `@atlas/plugin-flows`: FlowStepModal picker

- [x] 6.1 Add Query/Event tiles to `KIND_TILES` in `plugins/flows/frontend/src/components/FlowStepModal.tsx`.
- [x] 6.2 Render the Query/Event tiles `disabled` with a tooltip ("Requires the APIs plugin") when the task 5.2 check reports `atlas.apis` absent/inactive.
- [x] 6.3 Add a single flat, filterable search field for the Query/Event tile's detail form, using task 5.1's clients, rendering each result's method/path (or channel) as primary text and owning API name as secondary text (two-line item, matching the visual reference from EventCatalog's flow editor).
- [x] 6.4 On selecting a result, store `query_ref`/`event_ref` on the step with its snapshot fields; support clearing the reference back to the plain Step type.

## 7. `@atlas/plugin-flows`: JSON grammar mirror

- [x] 7.1 Add `query_ref`/`event_ref` to `STEP_KEYS` and shape validation in `flowSteps.ts`/`flowStepSchema.ts`, mirroring the backend's field types.
- [x] 7.2 Extend the mutual-exclusion check in `validateFlowSteps()`/the JSON parser to the four-way rule, matching `validate_steps()`.

## 8. `core/frontend`: searchable entity lookup

- [x] 8.1 Add `filterable` to `RefSelect` in `core/frontend/src/components/RefSelect.tsx`, matching `TargetRefSelect`'s existing pattern in the same file.

## 9. Verify

- [x] 9.1 Run the full `flow-management`/`visual-flow-editor` spec-scenario suites (backend + frontend) and confirm every pre-existing scenario still passes unmodified.
- [x] 9.2 Run the new `flow-query-event-steps`/`api-endpoint-operation-search` scenario suites.
- [x] 9.3 Manually verify, via `docker compose -f docker-compose.dev.yml`: add a Query step (search, select, save, reload — icon/color/subtitle correct); add an Event step (same); a distribution/session without `atlas.apis` shows Query/Event tiles disabled with a tooltip and every other step kind unaffected; a Flow referencing a `removed` Endpoint still loads and re-saves.
- [x] 9.4 Confirm `atlas.flows`'s `plugin.py` `requires_plugins` is unchanged (still only `atlas.standard-catalog`) — the `atlas.apis` integration stays soft.
