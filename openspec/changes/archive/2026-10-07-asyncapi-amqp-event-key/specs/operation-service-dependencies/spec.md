## MODIFIED Requirements

### Requirement: Publishers & subscribers graph is scoped to the shared channel, not one Operation row
An Operation's Overview tab SHALL show a read-only graph aggregating every `active` `Operation` (including ones belonging to other API documents) that shares its `channel_address`, showing each aggregated Operation's linked Services (including each Operation's document-owner role implied by `direction`) as publisher or subscriber nodes, supporting pan, zoom, and fit-to-view, with no drag-repositioning, connection-creation, or deletion available in the inline graph. This graph SHALL also be viewable in a full-screen mode, in which nodes can be repositioned as specified by the dependency-graph-exploration capability but connections still cannot be created or deleted.

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

#### Scenario: A removed operation does not contribute to the graph
- **WHEN** an Operation on the channel has `status=removed`
- **THEN** its document owner's implied role and its linked Services are absent from the channel's graph and from the `/consumers` aggregation

#### Scenario: A revived operation contributes again
- **WHEN** a `removed` Operation becomes `active` again through re-import
- **THEN** its document owner's implied role and its linked Services appear in the channel's graph again

#### Scenario: Publisher and subscribers from separate documents form one graph
- **WHEN** API X has an active `send` Operation and APIs Y and Z each have an active `receive` Operation on `rk-a`, each API provided by a different Service
- **THEN** viewing any of the three Operations shows the provider of X as publisher and the providers of Y and Z as subscribers

