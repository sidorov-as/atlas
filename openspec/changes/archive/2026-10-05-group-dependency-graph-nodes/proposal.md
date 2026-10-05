## Why

The full-screen dependency graphs draw every linked Service as its own node, capped at 50. For an Endpoint or Operation used by dozens of Services that is a wall of nodes, and the question people actually ask ("which teams depend on this?") has no direct answer. Grouping Services by their owning team or by system gives an overview first and detail on demand.

## What Changes

- The full-screen Endpoint consumers graph and Operation publishers & subscribers graph gain a grouping control in the settings menu: **No grouping**, **Group by: Team** and **Group by: System**.
- With grouping on, Services are drawn as one group node per team or system, showing its name and the number of Services. Activating a group expands it in place and draws its Services; activating it again collapses it. Search never expands a group by itself.
- Grouping is on by default when the graph has at least 10 linked Services, and off below that. The user's choice overrides the default and is remembered per browser.
- A Service with no team or system for the chosen grouping, and a group that would hold a single Service, are drawn as plain Service nodes, not as groups.
- The full-screen graphs use only the **Columns** layout (the Rings layout and the layout choice are removed there; the compact inline graphs keep rings). Group cards stack in a column beside the center node, with an expanded group's Services in a block beside its card. Operations place publishers and their groups on the left of the channel and subscribers on the right, blocks opening outward.
- Full-screen edges become rounded step lines between node sides, as in the Flow and ER diagrams; the inline graphs keep straight edges.
- Activating a "+N more" node in full screen closes the full-screen view as it opens Linked Services.
- Search keeps highlighting matching Services. With grouping on, group counts are recomputed for the search, groups without a match are dimmed, and a group card reads "N of M matches".
- The consumers APIs accept a grouping and a group filter and return per-group counts, so a group's size and its members come from the server, not from the capped first page. The change is additive: requests without the new parameters behave as before.
- `design.md` records drill-down (replace the graph with one group's Services and a back link) as a considered alternative with a sketch.

Out of scope: grouping in the compact Overview graph, grouping by anything other than team or system, persisting expanded groups or positions, and changing the Linked Services tables.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dependency-graph-exploration`: grouping control and default threshold, group nodes with expand/collapse, single-Service and ungrouped fallbacks, group-aware search, the Columns-only full-screen layout with groups, rounded step edges, and "more" closing full screen.
- `endpoint-service-dependencies`: the consumers API reports group counts for a chosen grouping and filters Services by group.
- `operation-service-dependencies`: the consumers API reports group counts per role for a chosen grouping and filters participants by group.

## Impact

- Backend, `plugins/apis`: `api/schemas.py` and `api/views.py` (consumers query and response schemas), `consumers.py` (grouping of channel participants in memory), `ServiceSummaryOut` (system fields), and their tests.
- Frontend, `plugins/apis/frontend`: `CompactDependencyGraph` (control, expansion state, group node type), `EndpointConsumersGraph`, `OperationConsumersGraph`, `lib/graphLayouts.ts`, `lib/entities.ts`, `lib/types.ts`, and tests.
- Docs: the plugin documentation page that describes the dependency graphs.
- MCP tools read the extension points, not these routes, so they are unaffected.
