## Context

`plugins/apis` has three kinds of list and two graphs, and they disagree.

- **Lists.** The API's Endpoints tab calls `GET /api/apis/{id}/endpoints/`, which returns a bare array and has no pagination. The Operations tab calls the same kind of unpaginated endpoint and slices client-side with a gravity `Pagination` (15/30/50/100). The Linked Services tabs use server pagination (`page`, `page_size`, default 20, max 100, response `{count, numPages, perPage, page.objectList}`) but render the control only when `count > 20`.
- **Graphs.** `CompactDependencyGraph` is the shared shell. Each caller builds nodes with a fixed-radius ring formula (`RING_RADIUS = 220`, 180px-wide nodes), so spacing between neighbours is `2·220·sin(π/n)`: 114px at 12 nodes, 76px at 18. The compact view caps at 12 with a caption; the full-screen dialog renders every Service from the same already-loaded data.
- **Consumers APIs.** `GET /api/endpoints/{id}/consumers/` returns every linked Service in one response; its schema docstring says this was deliberate so a full-screen explorer would have all the data. `GET /api/operations/{id}/consumers/` aggregates participants in Python across every `ApiOperation` sharing the channel (`consumers.channel_participants`), including each operation's document-owner role, which exists in no table row.
- **MCP.** The MCP tools `get_endpoint_consumers` and `get_operation_consumers` call `extension_points.get_endpoint_consumers` / `get_operation_consumers`, not the REST controllers, so a change confined to the REST views does not touch them. (To confirm during implementation by reading `extension_points.py`.)
- `elkjs` and `dagre` are not dependencies of `plugins/apis/frontend`; `@xyflow/react` and `@gravity-ui/uikit` are.

## Goals / Non-Goals

**Goals:**
- Lists in the API detail page and Linked Services share one pagination control.
- A graph never loads or draws every linked Service.
- The compact graph stays readable without overlap; full screen offers two layouts, an auto-layout reset, and a search that works beyond the node cap.

**Non-Goals:**
- A "By team" grouped layout, ELK/dagre, or any new dependency.
- Persisting node positions.
- Server-side pagination of the Endpoints and Operations lists, or changing the Linked Services tables.
- Pagination for the MCP tools.

## Decisions

### 1. Endpoints and Operations lists paginate client-side
Slice the already-fetched array after filtering, using the same `Pagination` props as `OperationsListTab` (page size 15, options 15/30/50/100, `showInput`). The server already applies search, method, deprecated and status filters, so the array is what the user is looking at. Page resets to 1 when a filter or the page size changes.
- *Server pagination* changes the list contract (bare array to `Paginated`), touches every caller, and buys nothing until an API has thousands of endpoints. Rejected for now.
- *Infinite scroll* does not match any other list in the app.

The Operations list groups by channel after slicing, so a channel straddling a page boundary shows on both pages. This is existing behavior; it is now stated in the spec and left alone. Slicing by channel group instead would make page sizes uneven, which is a worse trade for the same list.

### 2. Linked Services keeps server pagination and gets the shared control
Extract the pagination footer into one small component used by the four tabs (Endpoints, Operations, and both Linked Services), taking `page`, `pageSize`, `total`, `onUpdate`. Linked Services passes `page_size` to the server, so the selector changes the request. Page and page size stay in the URL as today (`page`, plus `page_size`), and the tab shows the control whenever `count > 0`.
- *Make Linked Services client-side* would fetch every row to show 20 and throw away the existing server contract. Rejected.

### 3. The consumers APIs paginate and accept `search`
Both gain `page` (default 1), `page_size` (default 50, max 100) and `search`; both add `count` to the response. This is a contract change: a caller that used to get every Service now gets the first 50. The only first-party caller is the frontend (`entities.ts`), so this is acceptable; the schema docstrings that promise "unpaginated" are rewritten.

- **Endpoint consumers:** the existing queryset gets `search` (service title/name, case-insensitive) and Django `Paginator`, ordered as today (service title, then name). `services` is the requested page; `count` is the total after search.
- **Operation consumers:** participants are aggregated in Python, so `search` filters that list and the page slices it. The order is made explicit and stable: publishers before subscribers, then service title, then name. The response also carries `publisherCount` and `subscriberCount` (totals after search) so the compact and full-screen graphs can label "+N more" per arc without a second request.
- *Build the graph on the existing Linked Services list instead.* It already has search, team filter and pagination. Rejected: for Operations it omits document-owner implied roles and other APIs' operations on the same channel, which the graph must show; for Endpoints it would work but leave the two graphs on different data sources.
- *Leave `/consumers/` unpaginated and cap in the browser.* This is today's state and the reason for the request; the response grows with the number of linked Services.

### 3a. Search needs no extra endpoint
Full-screen search issues the same consumers request with `search=<text>`. The graph shows the union of the base page (50) and the search results (up to 50), highlighting nodes that match and dimming those that do not. Debounce input (300ms) and cancel the in-flight request on change. Clearing the search drops the extra nodes.

### 4. Node caps and the "more" node
- Compact graph: `MAX_COMPACT_NODES = 6` Services plus one "more" node when `count > 6`. At 7 ring positions the neighbour spacing is `2·220·sin(π/7) ≈ 191px`, wider than a 180px node, so the existing radius needs no change. The compact graph uses the first 6 of the page already loaded for the Overview tab; it does not issue its own request.
- The "more" node is a distinct node type (`more`) with no edge to a Service; clicking it calls an `onOpenFullscreen` callback from `CompactDependencyGraph`. `handleNodeClick` today navigates only for `type === 'service'`, so the new type needs its own branch in both graph callers.
- Full screen: `MAX_FULLSCREEN_NODES = 50`, counted across both roles for Operations. If `count` (after search) exceeds what is drawn, a "more" node reads "+N more in Linked Services" and navigates to the Linked Services tab with `search` pre-filled when a search is active.
- Operations: one "more" node per arc, each labelled with that role's remainder from `publisherCount` / `subscriberCount`. The 6/50 budget is shared across arcs, filled publishers first.
- The previous caption ("12 of 18 services shown") and `overflowLabel` prop are removed; the node carries that information.

### 5. Layouts are pure functions in the frontend
Two layout functions in a new `lib/graphLayouts.ts`, each `(centerNode, serviceNodes, options) => positions`:
- **Rings.** Ring `k` has radius `R0 + k·ΔR` with `R0 = 220` and capacity `floor(2π·R_k / (nodeWidth + gap))`; nodes fill ring 0, then ring 1, and so on. 18 nodes fit on two rings, 50 on four.
- **Columns.** The center node on the left, Services stacked in columns of at most 10 rows to its right, centered vertically. For Operations, publishers fill columns to the left of the center and subscribers to the right, keeping the publisher/subscriber split visible.

Operations' current arc formula becomes the Operations Rings layout, so the compact graph is unchanged apart from the cap.
- *ELK/dagre* handles arbitrary graphs, but this graph is a star; a hand-written placement is about 40 lines per layout and adds no dependency. Rejected for this iteration; `flows` and `database-schema` already use ELK if a grouped layout is wanted later.
- *Force-directed* has no benefit on a star and produces unstable positions between renders. Rejected.

### 6. Dragging, settings and auto-layout live in the dialog only
The full-screen `ReactFlow` uses `useNodesState` seeded from the active layout and sets `nodesDraggable`. A settings button in the dialog header (gear icon) opens a menu with the layout choice; an "Auto-layout" button re-runs the active layout and replaces all positions. Changing the layout also re-runs it. The inline graph keeps `nodesDraggable={false}`, `nodesConnectable={false}`. Connections can still not be created or deleted anywhere.
- The chosen layout is stored under one `localStorage` key (`atlas.apis.graphLayout`), read and written inside try/catch, falling back to Rings. Node positions are not stored; closing the dialog discards them.

### 7. Shared dialog logic stays in `CompactDependencyGraph`
The shell already owns the dialog, the deferred `fitView` mount, and the empty/loading/error states, so layout choice, auto-layout, search box and the node-type-agnostic "more" handling belong there. Each caller keeps its own `buildGraph` for node data and passes the layout functions. This is a larger prop surface than today; to keep it readable, the layout, search and "more" settings go in one options object.

## Risks / Trade-offs

- **[Consumers contract change]** A caller that expected every Service now gets 50 → the only first-party caller is the frontend; the docstring and the OpenAPI schema change with it, and the MCP path is separate. Checked again during implementation by searching for other users of these routes (tests, docs, skills).
- **[Operations pagination is in-memory]** `channel_participants` loads every operation on the channel and every usage before slicing → acceptable for the sizes a channel has; the work already happens today on every request. Moving it into SQL is a possible follow-up, not part of this change.
- **[Search latency in full screen]** Each keystroke batch is a request → debounce and abort previous requests; the base nodes stay visible while it loads.
- **[Drag state lost on layout change or re-fetch]** A new search result set re-seeds node positions only for new nodes; existing nodes keep their dragged positions, and only Auto-layout or a layout change resets everything.
- **[Rings at 50 nodes are dense]** Four rings are readable only with highlight; Columns is the alternative → search with highlight is part of the same change, and Columns is one click away.
- **[`localStorage` unavailable]** Private windows can throw → access is wrapped, and the layout simply falls back to Rings.
- **[Operations "more" per arc plus a shared cap]** With 49 publishers and 3 subscribers the cap leaves one subscriber drawn → publishers fill first; an arc with zero drawn nodes still gets its "more" node so subscribers are never invisible.

## Migration Plan

No data migration. Ship backend and frontend together: the frontend change depends on `count`, `search`, `publisherCount` and `subscriberCount`, and the backend change is safe on its own because the frontend already handles a response with fewer Services (it caps anyway). Rollback is a revert of the commit; no state is stored server-side.

## Open Questions

- ~~Whether `extension_points.get_endpoint_consumers` shares a helper with the REST controller that this change would also alter.~~ Settled: it builds its own queryset, and `get_operation_consumers` uses only `consumers.channel_participants`, which this change leaves untouched (search, ordering and paging live in the REST controller). The MCP path is unaffected.
- The exact row limit per column in Columns (10 in this design); adjust after seeing it with real node sizes.
