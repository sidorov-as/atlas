## MODIFIED Requirements

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
