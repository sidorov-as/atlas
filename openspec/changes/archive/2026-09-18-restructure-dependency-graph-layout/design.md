## Context

`EndpointOverviewTab.tsx` and `OperationOverviewTab.tsx` currently share the same structure: a top `flex` row (a main content column with Documentation/parameters/responses, plus a fixed 260px "Details" `aside`), followed by a full-width `EndpointConsumersGraph`/`OperationConsumersGraph` section at a fixed `GRAPH_HEIGHT = 480`. This diverges from the two-column layout the originating design spec called for (`local/endpoint-dependency-explorer-design-spec.md` §17-18: content ~65% / graph ~35%, min 360px, same row as the summary cards, collapsing to one column under ~1200px) — a drift `add-endpoint-dependency-explorer`'s `design.md` never explicitly called out or reversed.

`EndpointConsumersGraph.tsx` and `OperationConsumersGraph.tsx` are ~90% identical: loading `Skeleton`, error `Alert` + retry, empty-state placeholder with an optional "Link service" `Button`, a `height:480/border/borderRadius` wrapper, a `<ReactFlow>` element with identical read-only props (`nodesDraggable={false}`, `nodesConnectable={false}`, `elementsSelectable`, `fitView`, `minZoom={0.2}`), `<Background/>`, `<Controls showInteractive={false}/>`, and an overflow `<Panel position="top-right">` label. They diverge only in `buildGraph()` (single ring vs. role-split double arc) and node type components (`EndpointNode`/`ServiceNode` vs. `ChannelNode`/`ServiceRoleNode`).

Gravity UI's `Dialog` (this codebase's existing modal convention, e.g. `LinkServiceDialog.tsx`) has no native fullscreen size — `maxWidth` tops out at `'l'` (the `size` prop is deprecated). A near-viewport modal needs explicit sizing via `modalClassName`/inline style.

## Goals / Non-Goals

**Goals:**
- Two-column top-section layout for both Overview tabs, graph docked right, collapsing to one column below ~1200px viewport width.
- One shared graph-shell component carrying the ~90%-identical chrome (loading/error/empty/ReactFlow wrapper/overflow indicator/fullscreen control), consumed by both `EndpointConsumersGraph` and `OperationConsumersGraph`.
- A "Full screen" control on that shell opening a near-viewport modal with the same graph, uncapped.

**Non-Goals:**
- Unifying `buildGraph()` or the node type components between Endpoint and Operation graphs — their layouts (single ring vs. role-split arcs) and node semantics are genuinely different and stay separate.
- A dedicated graph-explorer route, search, or filtering (original design-spec §58-59's "full graph explorer" — its own URL, search, filters, minimap — stays a Non-Goal, as already decided in the archived `add-endpoint-dependency-explorer` change).
- Any backend/API change — the fullscreen view reuses the already-fetched `consumers`/`participants` payload client-side.

## Decisions

### 1. Shared shell owns chrome; domain graphs own layout math and node types
**Decision:** Extract a `CompactDependencyGraph` component (`plugins/apis/frontend/src/components/CompactDependencyGraph.tsx`) that owns: loading/error/empty-state rendering, the `<ReactFlow>` wrapper with the standard read-only props, the compact-view overflow `<Panel>`, and the new fullscreen `Dialog`. It takes already-built `nodes`/`edges`/`nodeTypes`/`onNodeClick` plus presentation props (`emptyMessage`, `canLinkService`/`onLinkService`, `overflowLabel`, and — for fullscreen — a second, uncapped `nodes`/`edges` pair) from each caller. `EndpointConsumersGraph`/`OperationConsumersGraph` shrink to just `buildGraph()` + their node components, calling `CompactDependencyGraph` with two graphs: the capped one for inline display and the uncapped one for fullscreen.

**Why:** The chrome is byte-for-byte duplicated today; the layout math is not and forcing it into one function would mean branching internally on which domain is being rendered — worse than two short, readable functions. This mirrors the split the proposal's Non-Goals already settled.

**Alternative considered:** A shared `useCompactGraphState()` hook instead of a wrapper component, leaving each file to render its own JSX. Rejected: the JSX (wrapper div, `<ReactFlow>`, `<Background/>`, `<Controls/>`, `<Panel/>`, `<Dialog/>`) is exactly the part that's duplicated; a hook would still leave that markup copy-pasted twice.

### 2. Fullscreen renders the same already-fetched data uncapped, not a re-fetch
**Decision:** `CompactDependencyGraph` receives both the capped graph (for the inline view) and an uncapped graph (for fullscreen) as two `buildGraph()` calls over the same `consumers`/`participants` prop already held by `EndpointOverviewTab`/`OperationOverviewTab` — no new network request when Full screen opens. `buildGraph()` in both `EndpointConsumersGraph` and `OperationConsumersGraph` takes a `limit?: number` (or equivalent) so the same function produces both variants.

**Why:** `consumers`/`participants` are already fetched in full by the parent Overview tab (the *compact* graph is the one that slices to `MAX_GRAPH_SERVICES`/`MAX_GRAPH_PARTICIPANTS`); there's no missing data to fetch for an uncapped view.

**Risk:** an API/Service with a very large number of dependents (hundreds) renders every node in the fullscreen `ReactFlow` canvas at once. → **Mitigation:** none needed for this change — `fitView`/`minZoom` already exist and this isn't a new problem this change introduces (React Flow's own viewport culling and the existing pan/zoom controls handle this at the fullscreen scale the same way they would if the compact cap were simply raised); revisit only if real usage surfaces a concrete performance complaint.

### 3. Fullscreen sizing: `Dialog` with explicit near-viewport `maxWidth`/`modalClassName`, not a new full-page route
**Decision:** Use Gravity UI's `<Dialog>` (matching `LinkServiceDialog.tsx`'s convention) with `hasCloseButton`, `fullWidth`, and a `modalClassName` applying an explicit large `width`/`height` (e.g. ~90vw/90vh) rather than the deprecated `size="l"` (which doesn't reach fullscreen) or a dedicated route.

**Why:** `Dialog`'s built-in sizing (`maxWidth: 's' | 'm' | 'l'`) has no fullscreen tier — confirmed against `@gravity-ui/uikit`'s `Dialog.d.ts`. Reusing `Dialog` keeps this consistent with the rest of the plugin's modal usage (`LinkServiceDialog`, `LinkOperationServiceDialog`) rather than introducing a second modal primitive or a route-based explorer (which is explicitly the deferred, larger Non-Goal).

**Alternative considered:** A dedicated `/apis/:apiId/endpoints/:endpointId/graph` route per the original design-spec §58. Rejected for this change — that's the full graph explorer's own scope (search, filters, minimap, deep-linkable focus), already a Non-Goal; a same-page modal delivers "see everything, not just 12" without that added surface.

### 4. Two-column top section is a layout-only change to `EndpointOverviewTab`/`OperationOverviewTab`
**Decision:** Restructure the top section into a CSS grid (`grid-template-columns: minmax(0, 2fr) minmax(360px, 1fr)`) holding the existing summary content (left) and `CompactDependencyGraph` (right), with a `@media`/container-query collapse to a single column under ~1200px. Path/Query/Header parameter tables, Responses, and (for Operation) the message/schema sections move to a full-width block below this grid row instead of sharing the left column with the graph's old position.

**Why:** Matches the source design-spec's grid ratio and breakpoint (§17-18) instead of inventing a new one, and fixes the actual complaint (graph reads as oversized because it's full-width and disconnected from the summary it describes).

## Risks / Trade-offs

- **[Risk]** Two call sites (`EndpointOverviewTab`, `OperationOverviewTab`) both need their own grid restructuring — not shared, since their non-graph content (Documentation vs. message/schema sections) differs enough that a shared layout wrapper would need as many escape hatches as it saves. → **Mitigation:** accepted duplication, consistent with the proposal's Non-Goal of not forcing the two tabs into one shared component; only the graph shell itself is shared.
- **[Risk]** `Dialog`'s `modalClassName`-based sizing is a workaround, not first-class fullscreen support from the library — a future `@gravity-ui/uikit` upgrade could change how `maxWidth`/`fullWidth` compose. → **Mitigation:** low blast radius (one component); revisit if an upgrade breaks it.
- **[Risk]** Raising the visible node count in fullscreen (no cap) could make the existing fixed `RING_RADIUS = 220` / arc layout look cramped for endpoints with e.g. 50+ consumers, since the radial math was tuned for ≤12 nodes. → **Mitigation:** out of scope to fix here — the cap-removal is explicitly what was asked for; if a specific API's fullscreen graph turns out unreadable at high node counts, that's a follow-up tuning pass on the layout formula (still no layout library needed, likely just a node-count-scaled radius), not a reason to reintroduce a cap.

## Open Questions

None outstanding — see "Non-Goals" for scope explicitly deferred rather than left open.
