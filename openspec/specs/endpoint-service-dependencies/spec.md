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
An Endpoint's Overview tab SHALL show a read-only graph with the Endpoint as the center node and each linked Service as a node with a directed edge from Service to Endpoint, supporting pan, zoom, and fit-to-view, with no drag-repositioning, connection-creation, or deletion available. This graph SHALL also be viewable in a full-screen mode.

#### Scenario: Edge direction reflects dependency direction
- **WHEN** the consumers graph is rendered for an Endpoint with linked Services
- **THEN** each edge points from the Service node to the Endpoint node, not the reverse

#### Scenario: Clicking a Service node navigates to that Service
- **WHEN** a user clicks a Service node in the consumers graph
- **THEN** the user is navigated to that Service's detail page

#### Scenario: Clicking the Endpoint node does not navigate away
- **WHEN** a user clicks the center Endpoint node
- **THEN** the user remains on the current Endpoint page

#### Scenario: Graph nodes cannot be edited
- **WHEN** a user attempts to drag a node, or draw or delete a connection, in the consumers graph (inline or full-screen)
- **THEN** no change occurs — the graph is display-only

#### Scenario: Empty graph shows a call to action instead of a blank canvas
- **WHEN** an Endpoint has no linked Services
- **THEN** its Overview shows an explanatory empty state with a "Link service" action, not an empty graph canvas

#### Scenario: Large consumer counts are capped on the compact inline graph
- **WHEN** an Endpoint has more than 12 linked Services and the graph is shown in its compact, inline form on the Overview tab
- **THEN** the compact graph shows at most 12 Service nodes plus an indicator of how many more exist, rather than rendering all of them

#### Scenario: Full screen shows every linked Service uncapped
- **WHEN** a user opens the consumers graph in full-screen mode
- **THEN** every linked Service is shown as a node, with no 12-node cap, using the same already-loaded data as the inline graph
- **AND** a visible close action returns the user to the Overview tab without navigating away from the Endpoint page

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
