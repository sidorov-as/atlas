## 1. Backend: paginated and searchable consumers APIs

- [x] 1.1 Read `extension_points.get_endpoint_consumers` / `get_operation_consumers` and confirm the MCP path shares no code with the REST controllers that this change alters; record the result in the design's open questions
- [x] 1.2 Add `page`, `page_size` (default 50, max 100) and `search` query schemas for the endpoint and operation consumers routes in `api/schemas.py`
- [x] 1.3 Endpoint consumers: apply `search` (service name/title, case-insensitive) and Django `Paginator` to the queryset in `EndpointConsumersController`, keeping the title-then-name order; add `count` to `EndpointConsumersOut` and rewrite its "unpaginated" docstring
- [x] 1.4 Operation consumers: filter `channel_participants()` output by `search`, order publishers first then by title then name, slice by page; add `count`, `publisherCount` and `subscriberCount` to `OperationConsumersOut` and rewrite its docstring
- [x] 1.5 Backend tests for both controllers: default cap of 50, later page, search narrowing page and totals, role totals independent of page, document-owner implied roles included, unknown id returns not found
- [x] 1.6 Search the repo (docs, skills, tests, e2e) for other callers of the two consumers routes and update any that assumed an unpaginated response

## 2. Frontend: shared pagination control and list tabs

- [x] 2.1 Extract the pagination footer from `OperationsListTab` into a shared component (`page`, `pageSize`, `total`, `onUpdate`; options 15/30/50/100, `showInput`)
- [x] 2.2 Endpoints tab: client-side pagination with the shared control; reset to page 1 on filter or page-size change; update `EndpointsListTab` tests
- [x] 2.3 Operations tab: switch to the shared control, keep slicing before grouping; add a test for a channel spanning a page boundary
- [x] 2.4 Linked Services tabs (Endpoint and Operation): use the shared control, show it whenever `count > 0`, send `page_size` to the server, keep `page` and `page_size` in the URL, default 15; update tests
- [x] 2.5 Update `lib/entities.ts` types and wrappers for the new consumers parameters and response fields (`count`, `publisherCount`, `subscriberCount`)

## 3. Frontend: layouts and the compact graph

- [x] 3.1 Add `lib/graphLayouts.ts` with the Rings layout (concentric rings sized by node width) and unit tests: no overlaps at 6, 18 and 50 nodes
- [x] 3.2 Add the Columns layout (columns of at most 10 rows beside the center) with a two-sided variant for Operations (publishers one side, subscribers the other) and unit tests
- [x] 3.3 Add a `more` node type and callback plumbing in `CompactDependencyGraph`; remove `overflowLabel` and its caption
- [x] 3.4 Endpoint graph: cap the compact graph at 6 Services plus a "+N more" node that opens full screen; update `EndpointConsumersGraph` tests
- [x] 3.5 Operation graph: cap at 6 across roles, one "more" node per side with undrawn participants using `publisherCount` / `subscriberCount`; update `OperationConsumersGraph` tests
- [x] 3.6 Confirm the compact graph shows no node overlap at 7 ring positions at the default radius, by checking the rendered graph in the browser

## 4. Frontend: full-screen graph

- [x] 4.1 Full-screen `ReactFlow` with `useNodesState`, draggable nodes, connections still disabled; inline graph stays non-draggable
- [x] 4.2 Settings control (gear) in the dialog header to choose Rings or Columns; layout re-runs on change
- [x] 4.3 "Auto-layout" button that resets every node to the current layout's positions
- [x] 4.4 Remember the layout in `localStorage` under one key, inside try/catch, falling back to Rings; tests for unavailable and invalid stored values
- [x] 4.5 Search box with 300ms debounce and request cancellation, issuing the consumers request with `search`; show the union of the base page and the matches, highlight matches, dim the rest; "no matching services" message; clearing removes search-only nodes and highlighting
- [x] 4.6 Cap the full-screen graph at 50 nodes (across roles for Operations) and draw a "+N more" node that navigates to the Linked Services tab with `search` pre-filled when a search is active
- [x] 4.7 Component tests for dragging, Auto-layout, layout persistence, search highlight and the over-cap "more" node, for both graphs

## 5. Verification

- [x] 5.1 Run backend and frontend test suites and `make format-check`; fix failures
- [x] 5.2 Manually check against the local stack with the demo catalog and a test API of 20 endpoints: pagination on all four tabs, graphs with 6, 18 and 60+ linked Services, both layouts, dragging then Auto-layout, search beyond the cap
- [x] 5.3 Update the plugin documentation page that describes the dependency graphs, if one exists

## 6. Follow-up (later)

- [x] 6.1 Link dialogs: disable already-linked Services using an exact server check instead of the first consumers page (`EndpointDetailPage` passes `consumers.services`, capped at 50, to the Endpoint dialog; the Operation dialog only knows the current Linked Services page). Query by `service_id`/search when the dialog opens, or add a lookup to the existing Linked Services list, and add tests for an Endpoint and an Operation with more than 50 links
