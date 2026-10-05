## ADDED Requirements

### Requirement: Full-screen dependency graphs offer a choice of layout
The full-screen view of the Endpoint consumers graph and of the Operation publishers & subscribers graph SHALL offer a layout choice of at least two layouts: Rings, which places Services on as many concentric rings as needed so that no two nodes overlap, and Columns, which places Services in columns beside the center node. The choice SHALL be made from a settings control in the full-screen view, and SHALL apply to the nodes currently drawn. The default layout SHALL be Rings.

#### Scenario: Rings layout never overlaps nodes
- **WHEN** a full-screen graph with 18 Service nodes uses the Rings layout
- **THEN** the nodes are placed on more than one ring and no two Service nodes overlap

#### Scenario: Columns layout beside the center node
- **WHEN** a user selects the Columns layout for an Endpoint consumers graph
- **THEN** the Endpoint node is placed on one side and Service nodes are stacked in columns on the other, with no overlap

#### Scenario: Operation Columns layout keeps roles apart
- **WHEN** a user selects the Columns layout for a publishers & subscribers graph
- **THEN** publishers are placed in columns on one side of the channel node and subscribers on the other

#### Scenario: Choosing a layout re-lays out the nodes
- **WHEN** a user changes the layout in the settings control
- **THEN** every node is moved to the position the chosen layout gives it, discarding any manual positions

### Requirement: The chosen layout is remembered per browser, positions are not
The system SHALL remember the layout the user last chose in the browser's local storage and use it the next time any full-screen dependency graph opens. It SHALL NOT remember node positions. When local storage is unavailable or holds an unknown value, the graph SHALL open with the default layout and SHALL NOT show an error.

#### Scenario: Layout choice survives closing the dialog
- **WHEN** a user selects Columns, closes the full-screen graph, and opens it again
- **THEN** the graph opens with the Columns layout

#### Scenario: Dragged positions do not survive closing the dialog
- **WHEN** a user drags a node, closes the full-screen graph, and opens it again
- **THEN** all nodes are at the positions the layout gives them

#### Scenario: Local storage is blocked
- **WHEN** the browser refuses access to local storage
- **THEN** the full-screen graph opens with the Rings layout and works normally

### Requirement: Nodes can be dragged in full screen and restored by Auto-layout
In the full-screen view, a user SHALL be able to drag Service nodes to new positions. The full-screen view SHALL provide an "Auto-layout" action that returns every node to the position the current layout gives it. The compact inline graph SHALL NOT allow dragging. Creating or deleting connections SHALL NOT be possible in either view.

#### Scenario: Drag in full screen
- **WHEN** a user drags a Service node in the full-screen graph
- **THEN** the node stays where it was dropped and no data changes

#### Scenario: Auto-layout restores positions
- **WHEN** a user has dragged several nodes and activates "Auto-layout"
- **THEN** every node returns to the position the current layout gives it

#### Scenario: Inline graph is not draggable
- **WHEN** a user attempts to drag a node in the compact inline graph
- **THEN** the node does not move

### Requirement: Full-screen graphs can search Services with highlighting
The full-screen view SHALL provide a search box. While it holds text, Services whose name or display name contains that text, case-insensitively, SHALL be highlighted and all other Services SHALL be dimmed. The search SHALL be answered by the server over all linked Services, not only the drawn ones, so a matching Service beyond the node cap is drawn and highlighted. Clearing the box SHALL remove the highlighting and any nodes added only because they matched.

#### Scenario: Matching Service is highlighted
- **WHEN** a user types part of a Service's display name into the search box
- **THEN** that Service's node is highlighted and the non-matching nodes are dimmed

#### Scenario: Match beyond the cap is revealed
- **WHEN** an endpoint has 120 linked Services, the graph draws 50, and the user searches for a Service that is not among them
- **THEN** the matching Service is added to the graph and highlighted

#### Scenario: No match
- **WHEN** the search text matches no Service
- **THEN** the graph shows a "no matching services" message and all nodes remain dimmed

#### Scenario: Clearing the search
- **WHEN** a user clears the search box
- **THEN** no node is highlighted or dimmed and nodes added only by the search are removed

### Requirement: Dependency graphs cap the drawn nodes and show a "more" node
A dependency graph SHALL NOT draw more than a fixed number of Service nodes: 6 in the compact inline graph and 50 in the full-screen graph, counted across publishers and subscribers together for Operations. When more linked Services exist than are drawn, the graph SHALL draw a "… +N more" node, where N is the number not drawn. In the compact graph, activating this node SHALL open the full-screen graph. In the full-screen graph, activating it SHALL navigate to the Linked Services tab of the same Endpoint or Operation, with the current search text pre-filled when a search is active.

#### Scenario: Compact graph shows 6 Services and a "more" node
- **WHEN** an Endpoint has 18 linked Services and its compact graph is shown
- **THEN** 6 Service nodes are drawn together with a node reading "+12 more"

#### Scenario: Compact "more" node opens full screen
- **WHEN** a user activates the "more" node in the compact graph
- **THEN** the full-screen graph opens

#### Scenario: No "more" node when everything fits
- **WHEN** an Endpoint has 6 or fewer linked Services
- **THEN** no "more" node is drawn

#### Scenario: Full screen over the cap links to Linked Services
- **WHEN** an Endpoint has 120 linked Services and the full-screen graph is open with the search box empty
- **THEN** 50 Service nodes and a "+70 more" node are drawn, and activating that node opens the Linked Services tab

#### Scenario: Search text carries to Linked Services
- **WHEN** a search is active in the full-screen graph and the user activates the "more" node
- **THEN** the Linked Services tab opens with the same text in its search field

#### Scenario: The "more" node is not a Service
- **WHEN** a "more" node is drawn
- **THEN** it has no connection to the center node and activating it never navigates to a Service page
