## Why

The compact dependency graph on the Endpoint and Operation Overview tabs (`EndpointConsumersGraph`/`OperationConsumersGraph`) renders as a full-width section below all other content, at a fixed 480px height — visually oversized and disconnected from the summary information (Details card) it relates to. The original UX spec this feature was built from (`local/endpoint-dependency-explorer-design-spec.md` §17-18, an external source `design.md` for the originating change explicitly translated onto this codebase's architecture but never fully reconciled on this specific point) places the graph as a right-hand column next to the Endpoint overview/Details cards, sized to the same height, collapsing below content only on narrow viewports. That placement never made it into the implementation, and both the Endpoint and Operation Overview tabs share the same drift, since they were built from the same template.

Separately, users with many linked Services/participants can never see the full dependency set today — the compact graph caps at 12 nodes with a "N more" indicator, and there is no way to see the rest without leaving the page.

## What Changes

- Restructure `EndpointOverviewTab` and `OperationOverviewTab` into a two-column layout for their top section: a left column (~65%, min-width preserved) holding the existing summary/Details content, and a right column (~35%, 360px minimum) holding the compact dependency graph, both the same height. Path/Query/Header parameters, Responses, and other full-width sections move below this row instead of sharing the left column with the graph's former position.
- Below a ~1200px viewport width, the graph collapses to a single column below the summary content instead of sitting beside it.
- Extract a shared graph shell component (loading/error/empty states, the ReactFlow wrapper with its standard read-only configuration, and the overflow indicator) used by both `EndpointConsumersGraph` and `OperationConsumersGraph`. Each keeps its own node-layout math (`buildGraph()`) and node type components, since the Endpoint graph (single ring around one center node) and the Operation graph (two role-split arcs around a channel node) are genuinely different shapes — only the surrounding chrome is unified.
- Add a "Full screen" control to the graph shell that opens the same already-loaded graph data in a modal (Gravity UI `Dialog`, this codebase's existing modal convention) sized to most of the viewport, with an explicit close action.
- The fullscreen view shows **all** linked Services/participants, without the 12-node cap the compact inline view applies. The compact view keeps its existing cap + overflow indicator unchanged.

**Non-goals:** no new backend/API surface (the fullscreen view reuses the already-fetched `consumers`/`participants` data); no dedicated graph-explorer route, search, or filtering (the original design-spec's §58-59 "full graph explorer" — its own URL, search, filters, minimap — remains out of scope, as already decided as a Non-Goal in the archived `add-endpoint-dependency-explorer` change); no changes to what data the graph displays beyond lifting the cap in fullscreen.

## Capabilities

### New Capabilities
(none — this changes how existing capabilities are presented, not what they cover)

### Modified Capabilities
- `endpoint-service-dependencies`: the compact consumers graph gains a fullscreen mode that shows all linked Services uncapped; the existing cap-at-12 behavior is scoped explicitly to the compact (non-fullscreen) view.
- `operation-service-dependencies`: the compact publishers/subscribers graph gains the equivalent fullscreen mode, with the same cap-scoping clarification for participants.

## Impact

- `plugins/apis/frontend/src/components/EndpointOverviewTab.tsx` — layout restructuring.
- `plugins/apis/frontend/src/components/OperationOverviewTab.tsx` — layout restructuring.
- `plugins/apis/frontend/src/components/EndpointConsumersGraph.tsx` — refactored onto the new shared shell; cap removed in fullscreen.
- `plugins/apis/frontend/src/components/OperationConsumersGraph.tsx` — refactored onto the new shared shell; cap removed in fullscreen.
- New shared component (exact name/location decided in design.md) under `plugins/apis/frontend/src/components/`.
- No backend, migration, or API contract changes.
- This is the first of two related changes; a follow-up change will add OpenAPI-derived fields to the Details card this change repositions, and is sequenced after this one lands to avoid repositioning that card twice.
