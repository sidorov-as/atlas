## ADDED Requirements

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

## MODIFIED Requirements

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
