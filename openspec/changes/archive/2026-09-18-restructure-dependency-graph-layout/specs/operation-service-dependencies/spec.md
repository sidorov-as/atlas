## MODIFIED Requirements

### Requirement: Publishers & subscribers graph is scoped to the shared channel, not one Operation row
An Operation's Overview tab SHALL show a read-only graph aggregating every `Operation` (including ones belonging to other API documents) that shares its `channel_address`, showing each aggregated Operation's linked Services (including each Operation's document-owner role implied by `direction`) as publisher or subscriber nodes, supporting pan, zoom, and fit-to-view, with no drag-repositioning, connection-creation, or deletion available. This graph SHALL also be viewable in a full-screen mode.

#### Scenario: Two operations on the same channel from different APIs share one graph
- **WHEN** Operation A (on API X, `direction=send`) and Operation B (on API Y, `direction=receive`) share the same `channel_address`
- **THEN** viewing either Operation's Overview shows one graph containing both APIs' implied/linked roles for that channel, not two separate single-sided graphs

#### Scenario: Publisher and subscriber nodes are visually distinguished
- **WHEN** the publishers/subscribers graph is rendered
- **THEN** publisher nodes and subscriber nodes are visually distinguishable by a label, not by color alone

#### Scenario: Clicking a Service node navigates to that Service
- **WHEN** a user clicks a Service node in the publishers/subscribers graph
- **THEN** the user is navigated to that Service's detail page

#### Scenario: Graph nodes cannot be edited
- **WHEN** a user attempts to drag a node, or draw or delete a connection, in the publishers/subscribers graph (inline or full-screen)
- **THEN** no change occurs — the graph is display-only

#### Scenario: Empty graph shows a call to action instead of a blank canvas
- **WHEN** a channel has no linked Services and no document-owner-implied roles beyond the current Operation's own
- **THEN** its Overview shows an explanatory empty state with a "Link service" action, not an empty graph canvas

#### Scenario: Large participant counts are capped on the compact inline graph
- **WHEN** a channel's aggregated publishers and subscribers exceed 12 nodes and the graph is shown in its compact, inline form on the Overview tab
- **THEN** the compact graph shows at most 12 nodes plus an indicator of how many more exist, rather than rendering all of them

#### Scenario: Full screen shows every participant uncapped
- **WHEN** a user opens the publishers/subscribers graph in full-screen mode
- **THEN** every aggregated publisher and subscriber is shown as a node, with no 12-node cap, using the same already-loaded data as the inline graph
- **AND** a visible close action returns the user to the Overview tab without navigating away from the Operation page
