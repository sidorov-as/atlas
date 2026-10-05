## Context

The previous change gave the full-screen graphs a node cap of 50, a search answered by the server, two layouts (Rings, Columns), dragging and Auto-layout. A graph still shows one node per Service, so an Endpoint with 60 consumers is a crowded picture even when capped, and it does not answer "which teams depend on this".

- `ServiceSummaryOut` carries `team`, `teamId`, `teamName` (the Service's owner Group) but no system.
- `GET /api/endpoints/{id}/consumers/` is a Django queryset with `search` and `Paginator`. `GET /api/operations/{id}/consumers/` aggregates participants in Python (`consumers.channel_participants`), filters by `search` and slices by page. Both return `count`; Operations also return `publisherCount` and `subscriberCount`.
- `CompactDependencyGraph` owns the dialog, layout choice, search and the `more` node. `lib/graphLayouts.ts` has `ringsLayout` and `columnsLayout` as pure functions. The layout choice lives in `localStorage` under `atlas.apis.graphLayout`.
- The Operations graph has two roles; its current "Rings" is two arcs, one per role.

## Goals / Non-Goals

**Goals:**
- Group Services by team or system in the full-screen graphs, expand a group in place, and keep the 50-node cap and search working.
- Group sizes are exact and come from the server.
- Both existing layouts handle groups; Operations group per role.

**Non-Goals:**
- Grouping in the compact Overview graph.
- Grouping by other attributes (tag, lifecycle) or nested groups.
- Persisting expanded groups or node positions.
- Changing the Linked Services tables.

## Decisions

### 1. Grouping is a server-answered view of the consumers API
Both consumers routes accept `group_by` (`team` | `system`) and `group_id`.

- `group_by` set, no `group_id`: the response adds `groups`, a list of `{id, name, count}` for every group holding **at least 2** matching Services, ordered by name. `services` (Endpoint) or `participants` (Operation) then holds only the Services that are *not* in such a group: those whose group is empty and those alone in their group. `count` still reports the total matching Services.
- `group_by` and `group_id` set: the response is the page of Services in that group, in the usual order, with `count` for that group. `search` still applies.
- Operations return `publisherGroups` and `subscriberGroups` instead of one `groups` list, because a team can appear on both sides with different counts. `group_id` combines with the existing role semantics through an additional `role` parameter (`publisher` | `subscriber`).
- Without `group_by` nothing changes.

The server folds one-Service groups into plain Services so the client never has to decide that rule, and so group counts and the Services list never double-count.

- *Return every Service with its group and group client-side.* The cap is the reason for this change; it would reload all Services. Rejected.
- *A separate `/groups/` route.* Duplicates `search` handling and the Operations aggregation. Rejected; one extra parameter is simpler.

### 2. Team is the Service's owner; System needs a new field
Team grouping uses the existing `team*` fields. System grouping needs the Service's system, so `ServiceSummaryOut` gains nullable `system`, `systemId`, `systemName`. A Service without a system is returned as a plain Service in `System` grouping, as in decision 1. Endpoint queries add `select_related` for the system; the Operations aggregation reads it where it already loads Services.

### 3. Group nodes and expansion live in the graph shell
A new node type `group` (name, count, color dot, chevron, expanded flag) is drawn next to Service nodes and `more` nodes. Activating it toggles expansion. First expansion requests `group_id` for that group and caches the page; later toggles reuse it. A group is drawn expanded only after the user toggles it: search and Group-by change never expand. Changing `group_by` or the search term clears the expansion state and cached pages.

Expanded Services count toward the 50-Service cap together with plain Services; group nodes do not. If an expanded group has more Services than the cap leaves room for, a `more` node sits at the end of that group's block and reads "+N more". Activating it opens Linked Services with the team filter pre-filled for Team grouping and with the group name as the search text for System grouping. This is the same navigation the existing `more` node does, scoped to the group; in full screen it also closes the dialog, since Linked Services is on the same page.

### 4. Default and persistence
Grouping defaults to `Team` when the total count is at least 10 and to `None` otherwise, evaluated each time the dialog opens with no stored choice. An explicit choice is stored in `localStorage` under `atlas.apis.graphGroupBy` (own key, same try/catch and fallback rules as the layout key). The stored value `none` (shown as "No grouping") means "never group", even above 10.

### 5. Search with groups
The search request is the consumers request with `group_by` and `search`: group counts are totals matching the search. The client draws groups with a match count and dims groups that dropped to zero (they stay visible so the structure does not jump). The label reads "N of M matches" where M is the group's size without search, known from the unsearched response the graph already holds. Expanded groups show only matching Services highlighted plus the rest of what was loaded for that group, dimmed.

### 6. Layouts with groups
`graphLayouts.ts` positions *items*, where an item is a plain node, a collapsed group or an expanded group with its member block. The full-screen graphs use only the Columns layout; the layout choice, the stored layout key and the full-screen Rings layout are gone. The compact inline graphs keep `ringsLayout`.
- **Endpoint:** the center node is on the left. Groups and plain nodes form level 1, one column on its right. An expanded group keeps its card in place and puts its Services in one column (level 2) on the outer side of the card, centered on it. Cards below it shift down by the block height, so nothing overlaps.
- **Operations:** the channel node is in the middle. Publisher groups and plain publishers form one column on the left, subscriber ones one column on the right, and an expanded group's column opens outward (away from the center).
- **One column per level:** an earlier version wrapped a column after 10 rows (carried over from the ungrouped layout) and laid a group's Services in a grid. With step edges that broke the tree: edges to the far columns ran behind the near ones and looked like links between Services. Strict levels keep every edge between neighbouring levels. A group of 50 Services makes a tall column; the canvas pans and zooms.
- **Edges:** full-screen edges are rounded step lines (`smoothstep`, corner radius 16) that leave and enter nodes on their left or right side, as in the Flow and ER diagrams. Nodes carry invisible `left` and `right` source and target handles for this; the compact graphs keep straight edges between centered handles.

*Rings with expanded groups* was built first and removed after trying it on a 66-consumer Endpoint: the member fans around several ring items crossed the center and each other, and looked chaotic. Columns is simpler and always readable.

### 7. Colors
Group dots use a stable color derived from the group id, from the palette the app already uses for tags, so a team keeps its color between graphs and sessions.

## Alternatives considered

### Drill-down instead of expansion
Activating a group replaces the graph with the center node and only that group's Services, with a "← All teams" link back.

```
 Level 1                                  Level 2 (after clicking "Payments Team")
                                          ← All teams
                ┌──────────────┐
            ┌───│ ● Booking    │          ┌──────────┐      ┌───────────────┐
            │   └──────────────┘          │ GET      │──────│ billing-api   │
 ┌────────┐ │   ┌──────────────┐          │ /invoices│      ├───────────────┤
 │ GET    │─┼───│ ● Payments  ›│   ───▶   │ 18 cons. │──────│ refunds       │
 │/invoice│ │   └──────────────┘          └──────────┘      ├───────────────┤
 └────────┘ │   ┌──────────────┐                            │ ledger-sync   │
            └───│ ● Listings   │                            └───────────────┘
                └──────────────┘
```

Simpler layout (one level at a time, no overlap handling, no mixed sizes) and a natural fit for very large groups. Rejected for now: the overview is lost the moment one group is opened, comparing two teams needs back-and-forth, and it makes drag state and search harder to reason about because the node set changes completely. It stays a candidate if expansion proves too crowded in practice; the server contract in decision 1 serves both.

### Group as an ELK compound node
Draw groups as boxes around their Services. Needs ELK or dagre, which `plugins/apis` does not depend on, and it shows every Service at once, which is the problem. Rejected.

## Risks / Trade-offs

- **[Expanded groups plus the 50 cap]** Opening several large groups hits the cap quickly → the group's own `more` node and Linked Services navigation, and a short note on the cap in the spec. Collapsing a group frees its budget.
- **[Operations in-memory grouping]** Grouping happens in Python on the already-aggregated participants → same cost class as `search` and the role counts today.
- **[`System` field coverage]** If many Services have no system, `System` grouping shows mostly plain nodes → acceptable and visible; the user can switch to `Team`.
- **[Group color stability]** Hash-based colors can collide for adjacent groups → acceptable, the name is always shown.
- **[Contract growth]** New parameters and response fields on both routes → additive and defaulting to the old behavior.

## Migration Plan

No data migration. Backend and frontend ship together; the frontend degrades to ungrouped nodes if a response lacks `groups`. Rollback is a revert.

## Open Questions

- Which stored value a user who chose "None" gets when the stored key is unreadable: none (default threshold applies). Settled in decision 4.
- Whether the System-grouping `more` node should open Linked Services with the system as a filter once that tab has one; today it falls back to search text.
