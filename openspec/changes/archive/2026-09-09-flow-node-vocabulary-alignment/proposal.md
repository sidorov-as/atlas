## Why

The Flow canvas's node-kind vocabulary was coined independently of the catalog vocabulary it actually renders, and now conflicts with it in ways that mislead rather than clarify: a Component of any subtype (service/website/library/worker) always renders as a fixed green "Service" node — literally the wrong type for three of the four subtypes; "Query" implies a read, but the node it labels can represent a POST or DELETE call just as easily; and a Flow node can silently point at an Endpoint or Operation that has since been removed or deprecated in the catalog, with no visual signal that the reference is stale. Separately, a Step node with no `summary` shifts its title to a different vertical position than one that has a summary, because the card centers whatever content it has as a block instead of anchoring it. This change consolidates a design review (see this change's originating conversation) into one coordinated fix across the `flows` and `apis` plugins.

## What Changes

- Rename Flow's `FlowNodeKind` values for consistency with catalog vocabulary: `service` → `component` (removes its literal collision with `ComponentType`'s own `service` value), `query` → an internal `call` key displayed as **"API Call"** (protocol-neutral, not implying a read). `event` is unchanged — explicitly kept as "Event" rather than renamed to "Operation" (see the catalog tab rename below for why that would now be wrong instead of right). This is a computed-value rename only; `FlowNodeKind` is never persisted, so no data migration is needed.
- Component-backed and API-backed Flow nodes render with the real subtype's icon and color (service/website/library/worker; openapi/grpc/asyncapi/graphql) instead of one fixed icon/color for every subtype.
- Catalog: the API detail page's "Endpoints" tab (shown for `openapi`-typed APIs) is relabeled **"Operations"**, matching the label already used for `asyncapi`-typed APIs. This is a UI copy change only — no backend model, field, or route renames.
- API Call and Event nodes' colored chip now shows the actual HTTP method (`GET`, `POST`, …) or direction (`Send`/`Receive`) instead of the generic word "API Call"/"Event". No color-mapping changes — the target scheme is already exactly what `METHOD_COLORS`/`METHOD_THEME` implement today.
- A new stale-reference indicator: an API Call or Event node whose referenced Endpoint/Operation has since become `removed`, or whose Endpoint has `deprecated: true`, now shows a warning icon with an explanatory tooltip. The stored reference is untouched — this is a read-only visual signal, not automatic node removal.
- Every node card's chip+title now render at a fixed vertical position regardless of whether a subtitle is present, instead of the whole content block re-centering when a subtitle is missing.
- Flow's `external` node kind gains clarifying tooltip text distinguishing it (a step with no catalog reference at all) from the catalog's unrelated `External` tag (a cataloged entity that happens to be third-party). No functional link is added between them.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `visual-flow-editor`: the node-type picker's tile names change (Service → Component, Query → API Call); node rendering changes for Component/API real-subtype color, API Call/Event chip text, the new stale-reference warning, and top-anchored card content.
- `flow-query-event-steps`: reading a Flow now additionally surfaces, per step with a `query_ref`/`event_ref`, the referenced Endpoint/Operation's current `status`/`deprecated` state — computed at read time via the existing `atlas_plugin_apis.extension_points.resolve_endpoint`/`resolve_operation` functions, without changing what is stored or how save-time validation resolves references.

## Impact

- `plugins/flows/frontend/src/lib/flowNodeKind.ts` — `FlowNodeKind` values, `FLOW_NODE_KIND_LABELS`/`FLOW_NODE_KIND_ICONS`, `ENTITY_REF_KIND_TO_NODE_KIND`.
- `plugins/flows/frontend/src/lib/flowNodePalette.ts` — new Component-subtype and API-subtype swatch tables (duplicated from core per the existing plugin import-boundary pattern that already duplicates `METHOD_THEME`/`DIRECTION_THEME`); no changes to `METHOD_COLORS`/`DIRECTION_COLORS` values themselves.
- `plugins/flows/frontend/src/components/FlowNodes.tsx` — `FLOW_NODE_TYPES` keys, `EntityNodeComponent`/`QueryNodeComponent`/`EventNodeComponent` rendering (real subtype + method/direction chip text + warning icon), `CARD_STYLE_BASE`/`NodeCard` layout (top-anchored content).
- `plugins/flows/frontend/src/components/FlowStepModal.tsx` — node-type picker tile labels; External tile's clarifying copy.
- `core/frontend/src/lib/icons.ts` / `core/frontend/src/lib/badges.ts` — read (not modified) as the source `COMPONENT_TYPE_ICONS`/`COMPONENT_TYPE_THEME`/`API_TYPE_ICONS`/`API_TYPE_THEME` tables that flows duplicates from.
- `plugins/apis/frontend/src/entityDetailTabs/api.tsx` — tab label change; `plugins/apis/frontend/src/pages/ApiDetailPage.test.tsx` — assertion text updates.
- `plugins/apis/backend/atlas_plugin_apis/extension_points.py` — `resolve_endpoint`/`resolve_operation` reused (not changed) as the read-time status lookup.
- `plugins/flows/backend/atlas_plugin_flows/` — Flow read path gains a computed status annotation per step reference; `plugins/flows/backend/atlas_plugin_flows/tests/importBoundary.test.ts`-equivalent checks stay satisfied (the new read-time lookup goes through the same `extension_points` surface `validate_steps()` already uses, not a new direct import).
- `openspec/specs/visual-flow-editor/spec.md`, `openspec/specs/flow-query-event-steps/spec.md` — requirement and scenario text.
- No changes to the persisted Flow `steps` JSON grammar (`entity_ref`/`external_label`/`query_ref`/`event_ref` field names, shapes, and save-time validation rules are all unchanged) and no changes to `ApiEndpoint`/`ApiOperation` backend models or fields.
