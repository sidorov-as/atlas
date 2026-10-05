## Purpose

Operation Service Dependencies is the `Service <-> Operation` link, owned by the `atlas.apis` plugin. It records which Services publish or subscribe to an Operation's channel via an explicit, plugin-owned `ServiceOperationUsage` record with its own `publisher`/`subscriber` role, and provides the UI (Linked Services tab, channel-scoped publishers/subscribers graph) to manage and visualize it.

## Requirements

### Requirement: Service-to-Operation usage is an explicit, plugin-owned link with a role
A Service's relationship to a specific Operation SHALL be recorded as an explicit `ServiceOperationUsage` link (service, operation, role, created-at, created-by), created and removed through dedicated endpoints rather than through the generic derived entity-relations system. `role` SHALL be either `publisher` or `subscriber`, asserted independently of the Operation's own `direction`.

#### Scenario: A service can be linked as a subscriber
- **WHEN** a Service with no prior link to an Operation is linked to it with `role=subscriber`
- **THEN** a `ServiceOperationUsage` row is created recording that Service, Operation, and role, with the acting user and timestamp

#### Scenario: A service can be linked as a publisher
- **WHEN** a Service with no prior link to an Operation is linked to it with `role=publisher`
- **THEN** a `ServiceOperationUsage` row is created recording that role, independent of the Operation's own `direction`

#### Scenario: Multiple services can hold the same role on one operation
- **WHEN** two different Services are each linked to the same Operation with `role=subscriber`
- **THEN** both links succeed, since more than one subscriber to the same channel is a valid, ordinary shape

#### Scenario: A service cannot be linked to the same operation with the same role twice
- **WHEN** a Service that already has a `ServiceOperationUsage` link to an Operation with a given role is linked to that same Operation with the same role again
- **THEN** the request is rejected rather than creating a duplicate link

#### Scenario: A service can hold both roles on the same operation
- **WHEN** a Service is linked to an Operation as `publisher` and separately as `subscriber`
- **THEN** both links succeed as two distinct `ServiceOperationUsage` rows

#### Scenario: Unlinking targets exactly one role
- **WHEN** a Service holding both `publisher` and `subscriber` links to an Operation is unlinked with a specific `role`
- **THEN** only the `ServiceOperationUsage` row for that role is removed, and the other role's link remains

#### Scenario: Role is not validated against the operation's direction
- **WHEN** a Service is linked to an Operation with a `role` that would be unusual given the Operation's `direction` (e.g. a second `publisher` on a `send` operation whose document owner is already the implied publisher)
- **THEN** the link is still created — `role` is asserted independently of `direction` and is not constrained by it in this change

### Requirement: The API document's own owning Service is never self-linked
The Service found via an Operation's API's `apiProvidedBy` relation SHALL NOT be recorded as a `ServiceOperationUsage` row for that Operation; its role SHALL instead be derived automatically from the Operation's `direction` (`send` implies publisher, `receive` implies subscriber) wherever that Operation's roles are displayed.

#### Scenario: Linking the document owner is rejected
- **WHEN** a request attempts to link an Operation's own `apiProvidedBy` Service to that Operation via `ServiceOperationUsage`
- **THEN** the request is rejected, since that Service's role is already implied by the Operation's `direction`

#### Scenario: The document owner's implied role appears in listings without a link row
- **WHEN** an Operation's publishers/subscribers are listed or graphed
- **THEN** its `apiProvidedBy` Service appears with its direction-implied role even though no `ServiceOperationUsage` row exists for it

### Requirement: Linked Services are searchable, filterable, and sortable
An Operation's Linked Services listing SHALL support searching by service name/display name, filtering by team and by role, and sorting by service name or team name (ascending/descending), with this state reflected in the URL.

#### Scenario: Search by service name
- **WHEN** a user searches Linked Services for a substring of a service's display name, case-insensitively
- **THEN** only matching services are shown

#### Scenario: Filter by role
- **WHEN** a user filters Linked Services to `role=publisher`
- **THEN** only Services linked with that role are shown

#### Scenario: Filter by team
- **WHEN** a user filters Linked Services to a specific team
- **THEN** only services on that team are shown

#### Scenario: Search and filter state is shareable via URL
- **WHEN** a user searches and filters the Linked Services tab and shares the resulting URL
- **THEN** opening that URL reproduces the same search text, role filter, team filter, and sort order

### Requirement: Linking and unlinking are permission-gated and hidden, not just disabled
The Link Service action and each row's Unlink action SHALL be visible only to a user holding `operationDependency.create` / `operationDependency.delete` respectively; a user without the permission SHALL NOT see the action at all.

#### Scenario: Read-only user sees no Link/Unlink actions
- **WHEN** a user without `operationDependency.create` or `operationDependency.delete` views an Operation's Linked Services tab
- **THEN** no "Link service" button and no per-row "Unlink" action are rendered

### Requirement: Publishers & subscribers graph is scoped to the shared channel, not one Operation row
An Operation's Overview tab SHALL show a read-only graph aggregating every `Operation` (including ones belonging to other API documents) that shares its `channel_address`, showing each aggregated Operation's linked Services (including each Operation's document-owner role implied by `direction`) as publisher or subscriber nodes, supporting pan, zoom, and fit-to-view, with no drag-repositioning, connection-creation, or deletion available in the inline graph. This graph SHALL also be viewable in a full-screen mode, in which nodes can be repositioned as specified by the dependency-graph-exploration capability but connections still cannot be created or deleted.

#### Scenario: Two operations on the same channel from different APIs share one graph
- **WHEN** Operation A (on API X, `direction=send`) and Operation B (on API Y, `direction=receive`) share the same `channel_address`
- **THEN** viewing either Operation's Overview shows one graph containing both APIs' implied/linked roles for that channel, not two separate single-sided graphs

#### Scenario: Publisher and subscriber nodes are visually distinguished
- **WHEN** the publishers/subscribers graph is rendered
- **THEN** publisher nodes and subscriber nodes are visually distinguishable by a label, not by color alone

#### Scenario: Clicking a Service node navigates to that Service
- **WHEN** a user clicks a Service node in the publishers/subscribers graph
- **THEN** the user is navigated to that Service's detail page

#### Scenario: Inline graph nodes cannot be edited
- **WHEN** a user attempts to drag a node, or draw or delete a connection, in the inline publishers/subscribers graph
- **THEN** no change occurs — the graph is display-only

#### Scenario: Connections cannot be edited in full screen
- **WHEN** a user attempts to draw or delete a connection in the full-screen publishers/subscribers graph
- **THEN** no change occurs

#### Scenario: Empty graph shows a call to action instead of a blank canvas
- **WHEN** a channel has no linked Services and no document-owner-implied roles beyond the current Operation's own
- **THEN** its Overview shows an explanatory empty state with a "Link service" action, not an empty graph canvas

#### Scenario: Large participant counts are capped on the compact inline graph
- **WHEN** a channel's aggregated publishers and subscribers exceed 6 nodes and the graph is shown in its compact, inline form on the Overview tab
- **THEN** the compact graph shows at most 6 Service nodes plus, on each side that has undrawn participants, a "… +N more" node stating how many more exist on that side

#### Scenario: Full screen is capped at 50 participants across both roles
- **WHEN** a user opens the publishers/subscribers graph in full-screen mode for a channel with more than 50 participants
- **THEN** at most 50 Service nodes are shown across publishers and subscribers together, filled publishers first, plus a "… +N more" node on each side that has undrawn participants
- **AND** a visible close action returns the user to the Overview tab without navigating away from the Operation page

#### Scenario: A side with no drawn nodes still shows its "more" node
- **WHEN** a channel has 60 publishers and 3 subscribers and the 50-node budget is spent on publishers
- **THEN** the subscriber side shows a "+3 more" node, so subscribers are never invisible

#### Scenario: Full screen shows every participant when there are 50 or fewer
- **WHEN** a user opens the publishers/subscribers graph in full-screen mode for a channel with 18 participants
- **THEN** every participant is shown as a node and no "more" node is drawn

### Requirement: Cross-API aggregation respects each aggregated API's visibility
The channel-scoped publishers/subscribers graph and the `/consumers` aggregation SHALL exclude any aggregated `Operation` whose own `API` is not visible to the requesting principal, and SHALL do so without revealing that a hidden Operation exists (no count, placeholder node, or error naming it).

**Implementation note (verified, task 3.4):** no per-entity `API` visibility mechanism exists anywhere in this catalog — `openspec/specs/catalog-auth/spec.md` makes unrestricted read for any authenticated user an explicit requirement (v1 has no per-entity read ACL). This requirement is therefore currently unenforceable and unimplemented by design (user decision 2026-09-06, see the change's `design.md` Decision 7); the scenarios below describe intended behavior for if/when a real visibility mechanism is introduced, not current behavior.

#### Scenario: A restricted API's operation is excluded from another API's public graph
- **WHEN** a public `API`'s Operation and a restricted-visibility `API`'s Operation share the same `channel_address`, and a viewer without access to the restricted API views the public Operation's graph
- **THEN** the restricted API's Operation, its linked Services, and its document-owner implied role are all absent from the graph and from any node count shown, with no indication that a hidden participant exists

#### Scenario: A viewer with access to both APIs sees the full aggregation
- **WHEN** a viewer has read access to every `API` contributing an Operation to a shared `channel_address`
- **THEN** the graph and `/consumers` response include all of them, unaffected by the filter above

### Requirement: Linked Services reflects a removed operation's status
An Operation's Linked Services tab SHALL show a visible warning when the Operation itself has been removed (`status=removed`), rather than presenting its existing links as if the operation were still active.

#### Scenario: Linked Services warns for a removed operation
- **WHEN** a `removed` Operation's Linked Services tab is viewed and it still has linked Services
- **THEN** the tab displays a warning that the operation no longer exists in the API alongside the (still-listed) Services that depend on it

### Requirement: Linked Services reflects a deprecated operation's status
An Operation's Linked Services tab SHALL show a visible warning when the Operation itself is `deprecated` (via its manual override field), alongside (and independent of) the existing warning shown for a `removed` Operation.

#### Scenario: Linked Services warns for a deprecated operation
- **WHEN** a `deprecated` (but still `active`) Operation's Linked Services tab is viewed and it has linked Services
- **THEN** the tab displays a warning that the operation is deprecated, distinct from the removed-operation warning

#### Scenario: Deprecated and removed warnings are distinguishable
- **WHEN** an Operation is both `deprecated` and `removed`
- **THEN** its Linked Services tab shows both warnings, visually distinguished from one another

### Requirement: Graph failures do not block operation documentation
A failure loading the publishers/subscribers graph or the Linked Services list SHALL show an inline retry affordance in that section only, and SHALL NOT prevent the rest of the Operation page (Overview documentation, Message tab) from rendering.

#### Scenario: Graph load failure is isolated
- **WHEN** the publishers/subscribers graph data request fails
- **THEN** the graph section shows an inline error with a retry action while the operation's documentation sections render normally

### Requirement: Overview tab surfaces linked Services via the graph and a tab link, not a duplicate list
An Operation's Overview tab SHALL surface its linked Services only through the compact publishers/subscribers graph and a link to the dedicated Linked Services tab, not through a separate full or partial listing of linked Services embedded in Overview.

#### Scenario: Overview links to Linked Services instead of listing them
- **WHEN** a user views an Operation's Overview tab and it has one or more linked Services
- **THEN** Overview shows a "View all N services" link next to the publishers/subscribers graph that navigates to the Linked Services tab, rather than rendering the list of Services itself

#### Scenario: No services yet shows the graph's own empty state, not a second one
- **WHEN** an Operation has no linked Services
- **THEN** the publishers/subscribers graph's existing empty state (with its "Link service" action) is the only indication of this on Overview — no separate "no services linked" message is duplicated elsewhere on the tab

### Requirement: A Service-to-Operation link records its origin and source
Every `ServiceOperationUsage` link SHALL record an `origin`, either `manual` or `yaml`, and a `source`, either `ui` or `mcp`. `origin` SHALL default to `manual`; `yaml` is reserved for links declared by an ingested manifest, which this capability does not yet create. `source` SHALL be set by the server from the channel of the request that created the link (the REST API used by the web UI records `ui`, the MCP API records `mcp`) and SHALL NOT be taken from the request. Both fields SHALL be visible in Django admin and SHALL NOT appear in the web UI or in existing REST responses. Links that existed before this change SHALL be given `origin` `manual` and `source` `ui`.

#### Scenario: Link created from the web UI
- **WHEN** a Service is linked to an Operation through the REST API
- **THEN** the link has `origin` `manual` and `source` `ui`

#### Scenario: Client cannot choose the source
- **WHEN** a request body includes a `source` or `origin` value
- **THEN** it is ignored or rejected, and the stored values come from the server

#### Scenario: Pre-existing links are migrated
- **WHEN** the change is applied to a database that already has `ServiceOperationUsage` rows
- **THEN** each row has `origin` `manual` and `source` `ui`

#### Scenario: Admin shows origin and source
- **WHEN** an administrator opens a link in Django admin
- **THEN** its `origin` and `source` are shown

### Requirement: A YAML-origin Service-to-Operation link cannot be removed through the API
Removing a `ServiceOperationUsage` link whose `origin` is `yaml` through the REST API or an MCP tool SHALL be rejected with a message that the link is managed by ingestion, and the link SHALL remain. Removal of one role SHALL NOT be affected by the origin of the Service's link in the other role.

#### Scenario: Unlinking a YAML-origin link over REST
- **WHEN** a user unlinks a Service from an Operation with a role whose link has origin `yaml`
- **THEN** the request is rejected as a conflict and the link remains

#### Scenario: Origin is per role
- **WHEN** a Service holds a `yaml` link as publisher and a `manual` link as subscriber on one Operation, and the subscriber link is unlinked
- **THEN** the subscriber link is removed and the publisher link remains

### Requirement: Linked Services listing uses the shared pagination control
An Operation's Linked Services listing SHALL be paginated by the server and SHALL show the same pagination control as the API detail page lists: a page-size choice of 15, 30, 50 or 100 (default 15), and a page number input. The control SHALL be shown whenever the listing is not empty, not only when it exceeds one page. The current page and page size SHALL be reflected in the URL.

#### Scenario: Control is shown for a short list
- **WHEN** an Operation has 18 linked Services and its Linked Services tab is opened
- **THEN** the pagination control is shown, with the first 15 services on page 1 and 3 on page 2

#### Scenario: Page size is sent to the server
- **WHEN** a user selects 50 per page
- **THEN** the listing is requested from the server with that page size and shows up to 50 services

#### Scenario: Changing filters returns to the first page
- **WHEN** a user changes the search text, role filter, team filter or sort order
- **THEN** the listing shows page 1 of the new results

### Requirement: The channel participants data for the graph is paginated and searchable
The Operation consumers API that feeds the Overview graph SHALL accept `page`, `page_size` (default 50, at most 100) and `search`. It SHALL return the requested page of the channel's aggregated participants, ordered publishers first, then subscribers, each by display name then name. It SHALL report the total number of participants matching the search, and separately the number of publishers and the number of subscribers matching the search. `search` SHALL match a Service's name or display name, case-insensitively. A request without parameters SHALL return the first 50 participants, not every participant.

#### Scenario: Default request is capped
- **WHEN** a channel has 70 aggregated participants and its consumers are requested with no parameters
- **THEN** the response contains 50 participants and a total count of 70

#### Scenario: Role totals accompany the page
- **WHEN** a channel has 60 publishers and 10 subscribers
- **THEN** the response reports a publisher count of 60 and a subscriber count of 10 regardless of which page is returned

#### Scenario: Publishers come before subscribers
- **WHEN** the first page of a channel with both roles is requested
- **THEN** publishers appear before subscribers, and within each role Services are ordered by display name

#### Scenario: Document-owner implied roles are included
- **WHEN** a channel's Operation belongs to an API whose provider Service is its implied publisher
- **THEN** that Service is counted and returned as a publisher, as before

#### Scenario: Search narrows page and totals
- **WHEN** consumers are requested with `search=notif` and 3 participants match
- **THEN** the response contains those 3 participants and a total count of 3

### Requirement: The participant summary carries its system
The Service summary returned with an Operation's linked Services and channel participants SHALL include the Service's system reference, id and display name, or null when the Service has none.

#### Scenario: Participant with a system
- **WHEN** a channel participant belongs to the system "core"
- **THEN** its summary carries that system's reference, id and name

#### Scenario: Participant without a system
- **WHEN** a channel participant has no system
- **THEN** its system fields are null

### Requirement: The Service summary tolerates a Service without an owner
The Service summary returned with an Operation's linked Services and channel participants SHALL carry null team reference, id and name for a Service that has no owner, instead of failing the request.

#### Scenario: Participant without an owner
- **WHEN** a channel participant has no owner
- **THEN** the response succeeds and its team fields are null

### Requirement: The channel participants data can be grouped by team or system per role
The Operation consumers API SHALL accept `group_by` with the value `team` or `system`. With `group_by` and without `group_id`, the response SHALL include `publisherGroups` and `subscriberGroups`, each listing the teams or systems that hold at least two participants of that role matching `search`, with id, name and the number of matching participants of that role, ordered by name; the participants list SHALL then contain only matching participants not in a listed group of their own role, paginated and ordered as before, and `count` SHALL still be the total of all matching participants while `participantsCount` SHALL give the size of that list's remainder. With `group_by`, `group_id` and `role`, the response SHALL be the page of matching participants of that role in that group, with `count` set to that total. A request with `group_id` and without `role` SHALL be rejected as a validation error. Without `group_by`, the response SHALL be as before and SHALL NOT include group lists or `participantsCount`. An unsupported `group_by` value SHALL be rejected as a validation error. Document-owner implied roles SHALL be grouped like any other participant.

#### Scenario: Groups per role
- **WHEN** a channel has publishers from 3 teams with at least two Services each and subscribers from 4 such teams, and consumers are requested with `group_by=team`
- **THEN** `publisherGroups` lists 3 teams and `subscriberGroups` lists 4 teams, each with its role's count

#### Scenario: The same team on both sides
- **WHEN** a team has 3 publishers and 2 subscribers on the channel
- **THEN** it appears in `publisherGroups` with a count of 3 and in `subscriberGroups` with a count of 2

#### Scenario: Group members by group id and role
- **WHEN** consumers are requested with `group_by=team`, `group_id` of a team and `role=subscriber`
- **THEN** the response contains that team's subscribers on the channel and a count equal to their number

#### Scenario: Group id without role
- **WHEN** consumers are requested with `group_id` and no `role`
- **THEN** the response is a validation error

#### Scenario: Search narrows group counts
- **WHEN** consumers are requested with `group_by=team` and `search=notif` and 1 of a team's 3 subscribers matches
- **THEN** that team's entry in `subscriberGroups` is omitted if fewer than two matching participants remain, and its remaining participant is returned in the participants list

#### Scenario: No grouping requested
- **WHEN** consumers are requested without `group_by`
- **THEN** the response has no group lists and is otherwise unchanged

#### Scenario: Document-owner implied publisher is grouped
- **WHEN** the channel's provider Service is the implied publisher and shares a team with another publisher
- **THEN** both are counted in that team's publisher group
