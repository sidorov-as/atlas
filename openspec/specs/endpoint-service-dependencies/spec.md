## Purpose

Endpoint Service Dependencies is the `Service consumesEndpoint Endpoint` link, owned by the `atlas.apis` plugin. It refines the existing API-level `consumesAPI` relation to endpoint-level granularity via an explicit, plugin-owned `ServiceEndpointUsage` record, and provides the UI (Linked Services tab, compact consumers graph) to manage and visualize it.

## Requirements

### Requirement: Service-to-Endpoint usage is an explicit, plugin-owned link
A Service's use of a specific Endpoint SHALL be recorded as an explicit `ServiceEndpointUsage` link (service, endpoint, created-at, created-by), created and removed through dedicated endpoints rather than through the generic derived entity-relations system.

#### Scenario: A service can link to an endpoint it doesn't yet consume
- **WHEN** a Service with no prior link to an Endpoint is linked to it
- **THEN** a `ServiceEndpointUsage` row is created recording that Service and Endpoint, with the acting user and timestamp

#### Scenario: A service cannot be linked to the same endpoint twice
- **WHEN** a Service that already has a `ServiceEndpointUsage` link to an Endpoint is linked to that same Endpoint again
- **THEN** the request is rejected rather than creating a duplicate link

### Requirement: Linking a Service to an Endpoint ensures the corresponding consumesAPI
Linking a Service to an Endpoint SHALL ensure that Service's `consumesAPI` includes the Endpoint's API, creating that `consumesAPI` relation automatically if it does not already exist, using the existing generic Component spec-update path.

#### Scenario: consumesAPI is created automatically
- **WHEN** a Service with no existing `consumesAPI` on an API is linked to one of that API's Endpoints
- **THEN** the link succeeds, the response indicates a `consumesAPI` relation was also created, and `GET /api/apis/{apiId}/relations/` subsequently lists that Service as a consumer

#### Scenario: consumesAPI is not duplicated when it already exists
- **WHEN** a Service that already `consumesAPI` an API is linked to a second Endpoint of that same API
- **THEN** the link succeeds and no duplicate `consumesAPI` relation is created

### Requirement: Unlinking an Endpoint does not remove consumesAPI
Removing a `ServiceEndpointUsage` link SHALL NOT remove the Service's `consumesAPI` relation to that Endpoint's API, even if it was created automatically by that link.

#### Scenario: consumesAPI survives an unlink
- **WHEN** a Service's only `ServiceEndpointUsage` link to an API's Endpoints is removed
- **THEN** that Service's `consumesAPI` relation to the API remains present

### Requirement: Linked Services are searchable, filterable, and sortable
An Endpoint's Linked Services listing SHALL support searching by service name/display name, filtering by team, and sorting by service name or team name (ascending/descending), with this state reflected in the URL.

#### Scenario: Search by service name
- **WHEN** a user searches Linked Services for a substring of a service's display name, case-insensitively
- **THEN** only matching services are shown

#### Scenario: Filter by team
- **WHEN** a user filters Linked Services to a specific team
- **THEN** only services on that team are shown

#### Scenario: Default sort
- **WHEN** an Endpoint's Linked Services tab is opened with no sort specified
- **THEN** services are sorted by display name ascending, falling back to name when display name is absent

#### Scenario: Search and filter state is shareable via URL
- **WHEN** a user searches and filters the Linked Services tab and shares the resulting URL
- **THEN** opening that URL reproduces the same search text, team filter, and sort order

### Requirement: Linking and unlinking are permission-gated and hidden, not just disabled
The Link Service action and each row's Unlink action SHALL be visible only to a user holding `endpointDependency.create` / `endpointDependency.delete` respectively; a user without the permission SHALL NOT see the action at all.

#### Scenario: Read-only user sees no Link/Unlink actions
- **WHEN** a user without `endpointDependency.create` or `endpointDependency.delete` views an Endpoint's Linked Services tab
- **THEN** no "Link service" button and no per-row "Unlink" action are rendered

### Requirement: Compact consumers graph shows Service-to-Endpoint edges
An Endpoint's Overview tab SHALL show a read-only graph with the Endpoint as the center node and each linked Service as a node with a directed edge from Service to Endpoint, supporting pan, zoom, and fit-to-view, with no drag-repositioning, connection-creation, or deletion available in the inline graph. This graph SHALL also be viewable in a full-screen mode, in which nodes can be repositioned as specified by the dependency-graph-exploration capability but connections still cannot be created or deleted.

#### Scenario: Edge direction reflects dependency direction
- **WHEN** the consumers graph is rendered for an Endpoint with linked Services
- **THEN** each edge points from the Service node to the Endpoint node, not the reverse

#### Scenario: Clicking a Service node navigates to that Service
- **WHEN** a user clicks a Service node in the consumers graph
- **THEN** the user is navigated to that Service's detail page

#### Scenario: Clicking the Endpoint node does not navigate away
- **WHEN** a user clicks the center Endpoint node
- **THEN** the user remains on the current Endpoint page

#### Scenario: Inline graph nodes cannot be edited
- **WHEN** a user attempts to drag a node, or draw or delete a connection, in the inline consumers graph
- **THEN** no change occurs — the graph is display-only

#### Scenario: Connections cannot be edited in full screen
- **WHEN** a user attempts to draw or delete a connection in the full-screen consumers graph
- **THEN** no change occurs

#### Scenario: Empty graph shows a call to action instead of a blank canvas
- **WHEN** an Endpoint has no linked Services
- **THEN** its Overview shows an explanatory empty state with a "Link service" action, not an empty graph canvas

#### Scenario: Large consumer counts are capped on the compact inline graph
- **WHEN** an Endpoint has more than 6 linked Services and the graph is shown in its compact, inline form on the Overview tab
- **THEN** the compact graph shows 6 Service nodes plus a "… +N more" node stating how many more exist, rather than rendering all of them

#### Scenario: Full screen is capped at 50 Services
- **WHEN** a user opens the consumers graph in full-screen mode for an Endpoint with more than 50 linked Services
- **THEN** 50 Service nodes are shown, plus a "… +N more" node leading to the Linked Services tab
- **AND** a visible close action returns the user to the Overview tab without navigating away from the Endpoint page

#### Scenario: Full screen shows every linked Service when there are 50 or fewer
- **WHEN** a user opens the consumers graph in full-screen mode for an Endpoint with 18 linked Services
- **THEN** every linked Service is shown as a node and no "more" node is drawn

### Requirement: Linked Services reflects a removed endpoint's status
An Endpoint's Linked Services tab and consumers graph SHALL show a visible warning when the Endpoint itself has been removed (`status=removed`), rather than presenting its existing links as if the endpoint were still active.

#### Scenario: Linked Services warns for a removed endpoint
- **WHEN** a `removed` Endpoint's Linked Services tab is viewed and it still has linked Services
- **THEN** the tab displays a warning that the endpoint no longer exists in the API alongside the (still-listed) Services that depend on it

### Requirement: Linked Services reflects a deprecated endpoint's status
An Endpoint's Linked Services tab and consumers graph SHALL show a visible warning when the Endpoint itself is `deprecated`, alongside (and independent of) the existing warning shown for a `removed` Endpoint, so a consumer of a still-active-but-deprecated Endpoint sees the same signal an Endpoint's own detail page already shows.

#### Scenario: Linked Services warns for a deprecated endpoint
- **WHEN** a `deprecated` (but still `active`) Endpoint's Linked Services tab is viewed and it has linked Services
- **THEN** the tab displays a warning that the endpoint is deprecated, distinct from the removed-endpoint warning

#### Scenario: Deprecated and removed warnings are distinguishable
- **WHEN** an Endpoint is both `deprecated` and `removed`
- **THEN** its Linked Services tab shows both warnings, visually distinguished from one another

### Requirement: Graph failures do not block endpoint documentation
A failure loading the consumers graph or the Linked Services list SHALL show an inline retry affordance in that section only, and SHALL NOT prevent the rest of the Endpoint page (Overview documentation, Request, Response tabs) from rendering.

#### Scenario: Graph load failure is isolated
- **WHEN** the consumers-graph data request fails
- **THEN** the graph section shows an inline error with a retry action while the endpoint's documentation sections render normally

### Requirement: Overview tab surfaces linked Services via the graph and a tab link, not a duplicate list
An Endpoint's Overview tab SHALL surface its linked Services only through the compact consumers graph and a link to the dedicated Linked Services tab, not through a separate full or partial listing of linked Services embedded in Overview.

#### Scenario: Overview links to Linked Services instead of listing them
- **WHEN** a user views an Endpoint's Overview tab and it has one or more linked Services
- **THEN** Overview shows a "View all N services" link next to the consumers graph that navigates to the Linked Services tab, rather than rendering the list of Services itself

#### Scenario: No services yet shows the graph's own empty state, not a second one
- **WHEN** an Endpoint has no linked Services
- **THEN** the consumers graph's existing empty state (with its "Link service" action) is the only indication of this on Overview — no separate "no services linked" message is duplicated elsewhere on the tab

### Requirement: A Service-to-Endpoint link records its origin and source
Every `ServiceEndpointUsage` link SHALL record an `origin`, either `manual` or `yaml`, and a `source`, either `ui` or `mcp`. `origin` SHALL default to `manual`; `yaml` is reserved for links declared by an ingested manifest, which this capability does not yet create. `source` SHALL be set by the server from the channel of the request that created the link (the REST API used by the web UI records `ui`, the MCP API records `mcp`) and SHALL NOT be taken from the request. Both fields SHALL be visible in Django admin and SHALL NOT appear in the web UI or in existing REST responses. Links that existed before this change SHALL be given `origin` `manual` and `source` `ui`.

#### Scenario: Link created from the web UI
- **WHEN** a Service is linked to an Endpoint through the REST API
- **THEN** the link has `origin` `manual` and `source` `ui`

#### Scenario: Client cannot choose the source
- **WHEN** a request body includes a `source` or `origin` value
- **THEN** it is ignored or rejected, and the stored values come from the server

#### Scenario: Pre-existing links are migrated
- **WHEN** the change is applied to a database that already has `ServiceEndpointUsage` rows
- **THEN** each row has `origin` `manual` and `source` `ui`

#### Scenario: Admin shows origin and source
- **WHEN** an administrator opens a link in Django admin
- **THEN** its `origin` and `source` are shown

### Requirement: A YAML-origin Service-to-Endpoint link cannot be removed through the API
Removing a `ServiceEndpointUsage` link whose `origin` is `yaml` through the REST API or an MCP tool SHALL be rejected with a message that the link is managed by ingestion, and the link SHALL remain.

#### Scenario: Unlinking a YAML-origin link over REST
- **WHEN** a user unlinks a Service from an Endpoint and that link has origin `yaml`
- **THEN** the request is rejected as a conflict and the link remains

### Requirement: Linked Services listing uses the shared pagination control
An Endpoint's Linked Services listing SHALL be paginated by the server and SHALL show the same pagination control as the API detail page lists: a page-size choice of 15, 30, 50 or 100, with 15 as the default, and a page number input. The control SHALL be shown whenever the listing is not empty, not only when it exceeds one page. The current page and page size SHALL be reflected in the URL.

#### Scenario: Control is shown for a short list
- **WHEN** an Endpoint has 18 linked Services and its Linked Services tab is opened
- **THEN** the pagination control is shown, with the first 15 services on page 1 and 3 on page 2

#### Scenario: Page size is sent to the server
- **WHEN** a user selects 50 per page
- **THEN** the listing is requested from the server with that page size and shows up to 50 services

#### Scenario: Page and page size are shareable via URL
- **WHEN** a user opens page 2 at 30 per page and shares the URL
- **THEN** opening that URL shows page 2 at 30 per page

#### Scenario: Changing filters returns to the first page
- **WHEN** a user changes the search text, team filter or sort order
- **THEN** the listing shows page 1 of the new results

### Requirement: The consumers data for the graph is paginated and searchable
The Endpoint consumers API that feeds the Overview graph SHALL accept `page`, `page_size` (default 50, at most 100) and `search`, SHALL return the requested page of linked Services in the same order as before (display name, then name), and SHALL report the total number of linked Services matching the search. `search` SHALL match a Service's name or display name, case-insensitively. A request without parameters SHALL return the first 50 Services, not every Service.

#### Scenario: Default request is capped
- **WHEN** an Endpoint has 120 linked Services and its consumers are requested with no parameters
- **THEN** the response contains 50 Services and a total count of 120

#### Scenario: Requesting a later page
- **WHEN** consumers are requested with `page=2` and `page_size=50` for an Endpoint with 120 linked Services
- **THEN** the response contains Services 51 to 100 in the default order

#### Scenario: Search narrows both the page and the total
- **WHEN** consumers are requested with `search=pay` and 4 linked Services have "pay" in their name or display name
- **THEN** the response contains those 4 Services and a total count of 4

#### Scenario: Unknown Endpoint
- **WHEN** consumers are requested for an Endpoint that does not exist
- **THEN** the response is a not-found error, as before

### Requirement: The Service summary carries its system
The Service summary returned with an Endpoint's linked Services and consumers SHALL include the Service's system reference, id and display name, or null when the Service has none.

#### Scenario: Service with a system
- **WHEN** a linked Service belongs to the system "core"
- **THEN** its summary carries that system's reference, id and name

#### Scenario: Service without a system
- **WHEN** a linked Service has no system
- **THEN** its system fields are null

### Requirement: The Service summary tolerates a Service without an owner
The Service summary returned with an Endpoint's linked Services and consumers SHALL carry null team reference, id and name for a Service that has no owner, instead of failing the request.

#### Scenario: Service without an owner
- **WHEN** a linked Service has no owner
- **THEN** the response succeeds and its team fields are null

### Requirement: The consumers data can be grouped by team or system
The Endpoint consumers API SHALL accept `group_by` with the value `team` or `system`. With `group_by` and without `group_id`, the response SHALL include `groups`, one entry per team or system that holds at least two Services matching `search`, each with its id, name and the number of matching Services, ordered by name; the Services list SHALL then contain only matching Services not in any listed group (those without a team or system for the grouping, and those alone in their group), paginated as before, and `count` SHALL still be the total of all matching Services (grouped ones included) while `servicesCount` SHALL give the size of that list's remainder. With `group_by` and `group_id`, the response SHALL be the page of matching Services in that group, with `count` set to the group's matching total. Without `group_by`, the response SHALL be as before and SHALL NOT include `groups` or `servicesCount`. An unsupported `group_by` value SHALL be rejected as a validation error.

#### Scenario: Group counts accompany the ungrouped Services
- **WHEN** an Endpoint has 18 linked Services owned by 5 teams, 2 of them alone in their team, and consumers are requested with `group_by=team`
- **THEN** the response lists the 3 teams with at least two Services with their counts and returns the 2 single Services in the Services list

#### Scenario: Group members by group id
- **WHEN** consumers are requested with `group_by=team` and `group_id` set to a team that owns 4 linked Services
- **THEN** the response contains those 4 Services and a count of 4

#### Scenario: Search narrows group counts
- **WHEN** consumers are requested with `group_by=team` and `search=pay`, and 2 of a team's 5 Services match
- **THEN** that team's entry reports a count of 2

#### Scenario: Group by system
- **WHEN** consumers are requested with `group_by=system`
- **THEN** groups are the systems of the linked Services and Services without a system appear in the Services list

#### Scenario: No grouping requested
- **WHEN** consumers are requested without `group_by`
- **THEN** the response has no `groups` and is otherwise unchanged

#### Scenario: Unsupported grouping
- **WHEN** consumers are requested with `group_by=tag`
- **THEN** the response is a validation error

#### Scenario: Group members exceeding a page
- **WHEN** a group has 70 Services and its members are requested without `page_size`
- **THEN** the response contains the first 50 and a count of 70
