## 1. Backend: system on the Service summary

- [x] 1.1 Add nullable `system`, `systemId`, `systemName` to `ServiceSummaryOut` and fill them wherever a summary is built (Endpoint linked Services and consumers, Operation linked Services and participants); load the system without N+1 queries
- [x] 1.2 Backend tests for a Service with and without a system in each of the four responses

## 2. Backend: grouping in the consumers APIs

- [x] 2.1 Extend the consumers query schemas with `group_by` (`team` | `system`), `group_id` and, for Operations, `role`; reject an unsupported `group_by` and a `group_id` without `role` (Operations) or without `group_by`
- [x] 2.2 Endpoint consumers: with `group_by` and no `group_id`, return `groups` (at least two matching Services, ordered by name) and only the remaining Services in `services`, paginated; with `group_id`, return that group's page and total
- [x] 2.3 Operation consumers: same per role (`publisherGroups`, `subscriberGroups`), grouping the in-memory participants after `search`, including document-owner implied roles; add `role` filtering with `group_id`
- [x] 2.4 Update the response schemas and docstrings; keep requests without `group_by` byte-for-byte unchanged
- [x] 2.5 Backend tests: counts, single-Service folding, Services without team/system, search narrowing counts, group page and total, a group larger than a page, same team on both roles, validation errors, unknown id
- [x] 2.6 Search the repo (docs, skills, tests) for callers of the consumers routes and confirm the MCP path is unaffected

## 3. Frontend: types, API wrappers and persistence

- [x] 3.1 Update `lib/types.ts` (`ServiceSummary` system fields, group entries, `groups`, `publisherGroups`, `subscriberGroups`) and `ConsumersParams` / `toConsumersQuery` in `lib/entities.ts` for `groupBy`, `groupId`, `role`
- [x] 3.2 Add the stored grouping choice (`atlas.apis.graphGroupBy`) next to the layout choice in `lib/graphLayouts.ts` or a sibling module: read/write inside try/catch, `none` as an explicit value, default rule "Team when count >= 10"; unit tests for blocked, invalid and missing values
- [x] 3.3 Derive a stable group color from the group id using the app's existing tag palette; unit test determinism

## 4. Frontend: group node and layouts

- [x] 4.1 Add a `group` node type (name, color dot, count, chevron, expanded state, "N of M matches", dimmed) and its handling in `CompactDependencyGraph`
- [x] 4.2 Extend `graphLayouts.ts` to place items (plain node, group, expanded group with member block): Columns with a member block beside the card and shifted neighbours; unit tests for no overlap with 0, 1 and 3 expanded groups
- [x] 4.3 Rings with groups: group cards on the rings and an expanded group's Services on an outer arc, growing a ring when the sector is too small; unit tests with 3, 10 and 30 members
- [x] 4.4 Two-sided Columns with groups for Operations (publisher groups left, subscriber groups right, blocks open outward); unit tests
- [x] 4.5 Operations full screen uses only two-sided Columns, hides the layout control and ignores a stored `rings` without rewriting it; test

## 5. Frontend: behavior in the full-screen graphs

- [x] 5.1 "Group by" control (None / Team / System) in the dialog header; apply the default rule when nothing is stored; persist an explicit choice
- [x] 5.2 Request grouped consumers (`groupBy`, `search`) and draw group nodes plus ungrouped Services; keep the 50-Service cap with group nodes excluded from it
- [x] 5.3 Expand and collapse in place: lazy request by `groupId` (and `role`), cache per group, no auto-expansion from search, layout or grouping changes, collapse everything when grouping or search text changes
- [x] 5.4 Per-group "+N more" node for a group beyond the cap, navigating to Linked Services with the team filter (Team) or the group name as search (System)
- [x] 5.5 Search with groups: counts "N of M matches", dim groups without matches and non-matching Services in expanded groups, clear restores
- [x] 5.6 Component tests for both graphs: default threshold at 9 and 10 Services, grouping choice persistence, expand and collapse, single-Service fallback, Service without system, search counts, cap and per-group "more", Operations per-role groups

## 6. Verification and docs

- [x] 6.1 Run backend and frontend test suites and `make format-check`; fix failures
- [x] 6.2 Manually check against the local stack with the demo catalog and a test Endpoint with 60+ consumers from at least 6 teams: grouping by Team and System, expand several groups in Columns and Rings, an Operation with publishers and subscribers from several teams, search with groups, Group by None
- [x] 6.3 Update the plugin documentation page that describes the dependency graphs

## 7. Follow-up after manual review

- [x] 7.1 Remove the full-screen Rings layout and the layout choice: Columns only for Endpoint and Operation, drop the stored layout key and `ringsItemsLayout`
- [x] 7.2 Close the full-screen dialog when a "+N more" node opens Linked Services
- [x] 7.3 Draw full-screen edges as rounded step lines between node sides (`smoothstep`, left/right handles); keep the inline graphs straight
- [x] 7.4 Rename the grouping menu entries to "No grouping", "Group by: Team", "Group by: System"
- [x] 7.5 Update specs, design and the documentation page; update and add component tests
- [x] 7.6 One column per level in the full-screen layout: no wrapping after 10 rows and a single column for an expanded group's Services, so step edges never pass behind other nodes
- [x] 7.7 Add image export (SVG|PNG, transparent background, grid) to the full-screen toolbar of both graphs, like the Flow and ER exports; declare `html-to-image` for the plugin; tests for the export function, the control and both graphs
