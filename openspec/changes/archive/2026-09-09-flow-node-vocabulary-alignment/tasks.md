## 1. Flow node-kind rename

- [x] 1.1 In `plugins/flows/frontend/src/lib/flowNodeKind.ts`: rename `FlowNodeKind`'s `'service'` → `'component'` and `'query'` → `'call'`; update `ENTITY_REF_KIND_TO_NODE_KIND` (`component` now maps to `'component'`), `FLOW_NODE_KIND_LABELS` (`component: 'Component'`, `call: 'API Call'`, `event: 'Event'` unchanged), `FLOW_NODE_KIND_ICONS`.
- [x] 1.2 In `plugins/flows/frontend/src/lib/flowNodePalette.ts`: rename `FLOW_NODE_PALETTE`'s `service` key → `component`; rename `METHOD_COLORS`-adjacent exports/functions referencing `query` (e.g. `queryMethodColors`) to their `call` equivalents, keeping the color values themselves unchanged.
- [x] 1.3 In `plugins/flows/frontend/src/components/FlowNodes.tsx`: rename `FLOW_NODE_TYPES` keys (`service`→`component`, `query`→`call`), rename `EntityFlowNode`'s Component-kind usage and `QueryNode`/`QueryNodeComponent` → `CallNode`/`CallNodeComponent`.
- [x] 1.4 Update `plugins/flows/frontend/src/components/FlowStepModal.tsx`'s node-type picker tiles: "Service" tile → "Component", "Query" tile → "API Call" (keep the tile's underlying selection value in sync with task 1.1's renamed kind).
- [x] 1.5 Grep the `plugins/flows/frontend` test suite for the string literals `'service'`, `'query'`, `"Service"`, `"Query"` used as Flow node-kind identifiers or rendered chip text, and update to `'component'`/`'call'`/`"Component"`/`"API Call"` as appropriate — do not touch unrelated uses (e.g. `ComponentType`'s own `'service'` value in core/standard-catalog code, or `query_ref`'s field name).

## 2. Real Component/API subtype identity on Flow nodes

- [x] 2.1 Confirm what data the `entity_ref` resolution feeding `EntityNodeComponent` (`FlowNodes.tsx:157-172`) currently fetches (likely just id/name for `refName`); extend it to also carry the resolved Component's `type` / API's `type` field.
- [x] 2.2 Duplicate `COMPONENT_TYPE_ICONS`/`COMPONENT_TYPE_THEME` (`core/frontend/src/lib/icons.ts`, `core/frontend/src/lib/badges.ts`) and `API_TYPE_ICONS`/`API_TYPE_THEME` into `plugins/flows/frontend/src/lib/flowNodePalette.ts`/`flowNodeKind.ts`, following the existing `METHOD_COLORS`/`DIRECTION_COLORS` duplication pattern and its file-header comment convention explaining why the duplication exists.
- [x] 2.3 Update `EntityNodeComponent`'s rendering (for the renamed `component`/`api` kinds) to resolve icon/color from the new per-subtype tables instead of the fixed one-color-per-kind `FLOW_NODE_PALETTE` entry, falling back to a neutral default when the subtype is unresolved.
- [x] 2.4 Add/update component tests covering: a `website`-typed Component renders with Website's icon/color (not Service's), a `worker`-typed Component likewise, and a `grpc`-typed API renders with gRPC's icon/color (not a generic API color).

## 3. API Call/Event chip text

- [x] 3.1 In the renamed `CallNodeComponent`/`EventNodeComponent` (`FlowNodes.tsx`), change the `label` passed to `NodeCard` from the static `FLOW_NODE_KIND_LABELS.call`/`.event` to the resolved `queryRef.method` / title-cased `eventRef.direction`, falling back to the generic label when the ref is unresolved (mirroring the existing `subtitle ? ... : undefined` pattern).
- [x] 3.2 Verify no changes are needed to `METHOD_COLORS`/`DIRECTION_COLORS` values — confirm the existing color assignments already match the reviewed target scheme before touching anything.
- [x] 3.3 Update/add tests asserting the chip text itself (not just border color) for a `POST` API Call node and a `send` Event node.

## 4. Catalog: unify Endpoints/Operations tab label

- [x] 4.1 In `plugins/apis/frontend/src/entityDetailTabs/api.tsx`, change the `openapi`-typed tab's `label: 'Endpoints'` (line ~110) to `label: 'Operations'`, leaving its `id`/`value`/route and `ApiEndpointsTab` component unchanged.
- [x] 4.2 Update `plugins/apis/frontend/src/pages/ApiDetailPage.test.tsx`'s `{ name: 'Endpoints' }` assertions (lines ~170, ~176) to `{ name: 'Operations' }`.
- [x] 4.3 Grep `plugins/apis/frontend` for any other UI copy or test literal still saying "Endpoints" as this tab's display name and update for consistency (backend model/field names like `ApiEndpoint`, `operation_id`, and routes stay unchanged).

## 5. Stale Endpoint/Operation reference indicator

- [x] 5.1 In `plugins/flows/backend/atlas_plugin_flows`, add read-time resolution: for a Flow being serialized for a read response, collect every step's `query_ref.endpoint`/`event_ref.operation` id, batch-resolve them (avoid an N+1 loop — one `filter(pk__in=...)` per kind, not a per-step call to `resolve_endpoint`/`resolve_operation`), and attach each resolved Endpoint's `status`/`deprecated` or Operation's `status` to the response alongside (not replacing) the stored snapshot.
- [x] 5.2 Guard the new code path the same way `_resolve_query_or_event_ref` already does — `django_apps.is_installed('atlas_plugin_apis')` — so a Flow read succeeds with no live status attached when `atlas.apis` isn't installed, per the `flow-query-event-steps` delta's scenario.
- [x] 5.3 Handle the case where a referenced Endpoint/Operation id no longer resolves at all (fully deleted) by omitting live status for that step rather than failing the whole Flow read.
- [x] 5.4 On the frontend, extend the Flow-loading code path to read the new live-status data alongside `steps`, and pass it down to `CallNodeComponent`/`EventNodeComponent`.
- [x] 5.5 Render an orange `TriangleExclamation` icon (reusing the visual precedent at `plugins/apis/frontend/src/pages/EndpointDetailPage.tsx:96-98`) with an explanatory tooltip on a Call/Event node whose live status indicates `removed` or `deprecated`; verify the step's stored `query_ref`/`event_ref` is never mutated as a side effect of rendering this.
- [x] 5.6 Add backend tests for: a Flow read surfacing a removed Endpoint's status, a deprecated Endpoint's status, a removed Operation's status, an active/non-deprecated reference, a reference that no longer resolves at all, and a read with `atlas.apis` not installed (per the `flow-query-event-steps` delta's scenarios).
- [x] 5.7 Add a frontend test/story for the warning icon + tooltip rendering on both a Call and an Event node.

## 6. Card content top-anchoring

- [x] 6.1 In `plugins/flows/frontend/src/components/FlowNodes.tsx`'s `CARD_STYLE_BASE`, change `justifyContent: 'center'` to top-anchor content (e.g. `'flex-start'`), keeping the fixed 84px card height unchanged.
- [x] 6.2 Visually verify (light and dark theme) that a 3-line card (chip+title+subtitle) is unaffected and a 2-line card (chip+title only, e.g. a Step with no summary) now shows its chip/title at the same Y-position as the 3-line card, with empty space only below the title.
- [x] 6.3 Update/add a test asserting chip/title vertical position is the same for a node with and without a subtitle.

## 7. External naming clarification

- [x] 7.1 In `plugins/flows/frontend/src/components/FlowStepModal.tsx`, add clarifying help text to the External tile explaining it represents a step with no catalog record at all, distinct from a catalog entity tagged `"External"`.
- [x] 7.2 Consider (and if straightforward, add) the same clarifying text as a tooltip on the rendered External node itself, not only in the picker.

## 8. Spec, docs, and final verification

- [x] 8.1 Confirm `openspec/specs/visual-flow-editor/spec.md` and `openspec/specs/flow-query-event-steps/spec.md` end up matching this change's delta specs after archive (no leftover "Service"/"Query" wording in requirement or scenario text).
- [x] 8.2 Run the full `plugins/flows` and `plugins/apis` frontend and backend test suites; fix any remaining literal-string breakage from the rename (task 1.5/4.3 sweeps are a starting point, not exhaustive).
- [x] 8.3 Manually verify in the running app (`/flows/{id}/edit`): node-type picker shows Component/API Call labels, a non-service Component subtype renders with correct icon/color, an API Call/Event chip shows its method/direction, a removed/deprecated reference shows the warning icon and tooltip, and a summary-less Step's title sits at the same position as one with a summary — before marking this change ready to archive.
