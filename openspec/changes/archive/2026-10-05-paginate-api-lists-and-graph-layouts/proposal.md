## Why

The API plugin's lists and dependency graphs stop working once an API or an endpoint has more than a couple of dozen items. The Endpoints tab on an API renders every endpoint with no pagination. The "Services using this endpoint" graph places nodes on a single ring of fixed radius, so 12 nodes already overlap in the compact view and 18 sit on top of each other in full screen. Linked Services is paginated on the server, but its control is hidden below 21 items and has no page-size choice, so it looks different from every other list. The consumers APIs that feed the graphs return every linked Service in one unbounded response.

## What Changes

- The Endpoints tab on an API detail page is paginated client-side with the same control as the Operations tab (15/30/50/100 per page, page input).
- The Operations tab on an API detail page keeps its client-side pagination, which is now specified. A channel group that straddles a page boundary is called out as a known limitation.
- The Linked Services tabs of Endpoint and Operation keep server-side pagination and get the shared control: a page-size selector (15/30/50/100), shown whenever the list is non-empty.
- The consumers APIs for an Endpoint and for an Operation's channel accept `page` and `page_size` and report the total count, so a graph never has to load every linked Service.
- The compact graphs on the Endpoint and Operation Overview tabs show at most 6 Service nodes plus a "… +N more" node. Clicking it opens the full-screen graph. This replaces the current 12-node cap and its "12 of 18 shown" caption.
- The full-screen graphs offer a layout choice (Rings with as many concentric rings as needed, or Columns), a settings control to pick it, and an "Auto-layout" action that restores the chosen layout after the user has dragged nodes. The chosen layout is remembered in the browser; node positions are not.
- Nodes become draggable in full screen only. The inline graphs stay display-only. **BREAKING** for the existing requirement that the graph offers no drag-repositioning in full screen.
- The full-screen graphs get a search box that highlights matching Services and dims the rest. Search runs on the server, so it finds Services beyond the displayed cap.
- The full-screen graphs render at most 50 nodes (for Operations, 50 across publishers and subscribers together). Beyond that, a "… +N more" node links to the matching Linked Services tab with the search text pre-filled.

Out of scope: a "By team" grouped layout and any new layout dependency (ELK or dagre), saving node positions, and changing the Linked Services tables beyond their pagination control.

## Capabilities

### New Capabilities
- `dependency-graph-exploration`: behavior shared by the Endpoint and Operation dependency graphs in full screen: layout choice and its persistence, auto-layout, in-graph dragging, server-side search with highlight, the node cap, and the "more" node.

### Modified Capabilities
- `api-endpoints`: the API detail page's endpoint list is paginated.
- `api-operations`: the API detail page's operation list is paginated, with the channel-straddle limitation stated.
- `endpoint-service-dependencies`: Linked Services pagination control; the compact graph cap changes from 12 to 6 with a "more" node; full screen is capped and no longer shows every Service; the consumers API is paginated; drag-repositioning is allowed in full screen.
- `operation-service-dependencies`: the same changes for the publishers & subscribers graph, with the compact and full-screen caps counted across both roles.

## Impact

- Frontend (`plugins/apis/frontend`): `EndpointsListTab`, `OperationsListTab`, `EndpointLinkedServicesTab`, `OperationLinkedServicesTab`, `CompactDependencyGraph`, `EndpointConsumersGraph`, `OperationConsumersGraph`, and the API wrappers in `lib/entities.ts`.
- Backend (`plugins/apis/backend`): the endpoint and operation consumers views gain pagination parameters and a total count. This is a response-shape change for any client of those endpoints; the design records how existing callers are kept working.
- No new dependencies. No database migrations.
- The MCP tools and skills that read consumers go through different endpoints and are not expected to change; the design confirms this.
