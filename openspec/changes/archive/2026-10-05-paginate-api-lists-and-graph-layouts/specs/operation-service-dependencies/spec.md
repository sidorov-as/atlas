## ADDED Requirements

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

## MODIFIED Requirements

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
