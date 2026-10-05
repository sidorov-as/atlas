## RENAMED Requirements
- FROM: `### Requirement: Full-screen dependency graphs offer a choice of layout`
- TO: `### Requirement: Full-screen dependency graphs use the Columns layout`
- FROM: `### Requirement: The chosen layout is remembered per browser, positions are not`
- TO: `### Requirement: The chosen grouping is remembered per browser, positions are not`

## MODIFIED Requirements

### Requirement: Full-screen dependency graphs use the Columns layout
The full-screen view of the Endpoint consumers graph SHALL place the center node on the left and the Services, or the groups when grouped, in a single column on its right, and SHALL NOT offer a choice of layout. The full-screen view of the Operation publishers & subscribers graph SHALL place the channel node in the middle, publishers in a single column on its left and subscribers in a single column on its right. Every level of the graph SHALL be one column, so each edge joins nodes of neighbouring levels. The compact inline graphs MAY keep their ring layout.

#### Scenario: Endpoint graph uses Columns
- **WHEN** a user opens the full-screen Endpoint consumers graph
- **THEN** the Endpoint node is placed on the left and the Service nodes are stacked in one column on its right with no overlap, and the settings control offers no layout choice

#### Scenario: Operation graph is two-sided Columns
- **WHEN** a user opens the full-screen publishers & subscribers graph
- **THEN** publishers are placed in a column on one side of the channel node, subscribers on the other, and the settings control offers no layout choice

#### Scenario: Auto-layout re-lays out the nodes
- **WHEN** a user activates Auto-layout
- **THEN** every node is moved to the position the layout gives it, discarding any manual positions

### Requirement: The chosen grouping is remembered per browser, positions are not
The system SHALL remember the grouping the user last chose in the browser's local storage and use it the next time any full-screen dependency graph opens. It SHALL NOT remember node positions or which groups are expanded. When local storage is unavailable or holds an unknown value, the graph SHALL open with the default grouping and SHALL NOT show an error.

#### Scenario: Grouping choice survives closing the dialog
- **WHEN** a user selects "Group by: System", closes the full-screen graph, and opens it again
- **THEN** the graph opens grouped by system

#### Scenario: Dragged positions and expanded groups do not survive
- **WHEN** a user drags a node and expands a group, closes the full-screen graph, and opens it again
- **THEN** all nodes are at the positions the layout gives them and every group is collapsed

#### Scenario: Local storage is blocked
- **WHEN** the browser refuses access to local storage
- **THEN** the full-screen graph opens with the default grouping and works normally

## ADDED Requirements

### Requirement: Full-screen graphs can group Services by team or system
The full-screen view SHALL provide a grouping control in its settings menu with the options "No grouping", "Group by: Team" and "Group by: System". With Team or System chosen, Services SHALL be drawn as one group node per team (the Service's owner) or per system, showing the group's name, a color mark and the number of Services in it, instead of one node per Service. A Service that has no team or system for the chosen grouping, and a group that would hold exactly one Service, SHALL be drawn as an ordinary Service node. With None chosen, Services SHALL be drawn individually as before. Group sizes SHALL be exact totals over all linked Services, not over the drawn ones.

#### Scenario: Services are grouped by team
- **WHEN** an Endpoint has 18 linked Services owned by 5 teams and the user chooses "Group by: Team"
- **THEN** 5 group nodes are drawn, each showing the team's name and its number of Services, and no individual Service node is drawn

#### Scenario: Group size counts all linked Services
- **WHEN** a team owns 70 of the Endpoint's 120 linked Services
- **THEN** its group node reads 70 Services

#### Scenario: A Service without a system stays visible
- **WHEN** the user groups by System and a linked Service has no system
- **THEN** that Service is drawn as an ordinary Service node beside the group nodes

#### Scenario: A single-Service group is not a group
- **WHEN** a team owns exactly one of the linked Services
- **THEN** that Service is drawn as an ordinary Service node, not as a group node

#### Scenario: None shows Services individually
- **WHEN** the user chooses "No grouping"
- **THEN** each linked Service is drawn as its own node, up to the full-screen node cap

### Requirement: Grouping is on by default for larger graphs
When the user has made no grouping choice, the full-screen graph SHALL group by Team if it has 10 or more linked Services and SHALL NOT group if it has fewer. A grouping the user has chosen, including None, SHALL override this default.

#### Scenario: Large graph opens grouped
- **WHEN** an Endpoint has 10 linked Services, the user has never chosen a grouping, and the full-screen graph opens
- **THEN** the graph is grouped by team

#### Scenario: Small graph opens ungrouped
- **WHEN** an Endpoint has 9 linked Services and the user has never chosen a grouping
- **THEN** the full-screen graph shows each Service as its own node

#### Scenario: Chosen None wins over the default
- **WHEN** the user chose "No grouping" earlier and opens the full-screen graph of an Endpoint with 40 linked Services
- **THEN** the graph is not grouped

### Requirement: A group expands in place and collapses again
Activating a group node SHALL draw that group's Services connected to the group node, and activating it again SHALL remove them. Expanding SHALL NOT remove other groups or collapse other expanded groups. Search, a layout change and a change of grouping SHALL NOT expand any group by themselves, and changing the grouping or the search text SHALL collapse all groups. The group's Services SHALL be loaded from the server by group, not taken from a capped page of all Services.

#### Scenario: Expanding a group
- **WHEN** a user activates the "Payments Team" group node
- **THEN** that team's Services are drawn next to the group node and the other group nodes remain

#### Scenario: Collapsing a group
- **WHEN** a user activates an expanded group node
- **THEN** its Services are removed and the group node remains

#### Scenario: Several groups open at once
- **WHEN** a user expands two groups
- **THEN** both show their Services and no two nodes overlap

#### Scenario: Search does not expand
- **WHEN** a user searches for a Service that belongs to a collapsed group
- **THEN** the group stays collapsed

#### Scenario: Large group exceeds the cap
- **WHEN** a user expands a group whose Services would take the drawn Services beyond 50
- **THEN** Services are drawn up to the cap and a "+N more" node ends the group's block, which opens the Linked Services tab for that group

### Requirement: Search works with groups
With a grouping active, the search box SHALL be answered by the server over all linked Services. Group nodes SHALL show the number of matching Services out of the group's total ("N of M matches"), groups with no match SHALL stay visible but dimmed, and an expanded group SHALL highlight its matching Services and dim the others.

#### Scenario: Group shows matches
- **WHEN** a user searches "pay" and 2 of the 5 Services in a group match
- **THEN** the group node reads "2 of 5 matches" and is not dimmed

#### Scenario: Group without matches is dimmed
- **WHEN** a user searches and no Service in a group matches
- **THEN** the group node stays visible and is dimmed

#### Scenario: Clearing the search
- **WHEN** a user clears the search box
- **THEN** group nodes show their plain size again and nothing is dimmed

### Requirement: Layouts place groups and expanded Services without overlap
The full-screen Columns layout SHALL place group nodes, ordinary Service nodes and the Services of expanded groups so that no two nodes overlap: group nodes and ordinary Services stack in a column beside the center node, an expanded group's Services are placed in one column beside its group node, centered on it, and the nodes below it are shifted down so the blocks do not overlap. For Operations, publisher groups and publishers SHALL be placed on one side of the channel node and subscriber groups and subscribers on the other, each expanded group's Services opening away from the center.

#### Scenario: Expanded group
- **WHEN** a user expands a group of 12 Services
- **THEN** the Services form one column beside the group node, the group nodes below it move down, and no nodes overlap

#### Scenario: Several groups open
- **WHEN** a user expands two groups
- **THEN** both show their Services in columns at the same level and no two nodes overlap

#### Scenario: Edges never pass behind other nodes
- **WHEN** a group of 15 Services is expanded
- **THEN** all 15 Services are in one column and each edge runs from the group node straight to its Service

#### Scenario: Operation groups by role
- **WHEN** a channel has publishers from 3 teams and subscribers from 4 teams and the graph is grouped by team
- **THEN** 3 publisher group nodes are on one side of the channel node and 4 subscriber group nodes on the other

#### Scenario: Expanded group in an Operation graph
- **WHEN** a user expands a subscriber group
- **THEN** its Services open on the outer side of the group node, away from the channel node

### Requirement: Full-screen graphs draw rounded step edges
The full-screen graphs SHALL draw each edge as a step line with rounded corners that leaves and enters nodes on their left or right side, in the style of the Flow and ER diagrams. The compact inline graphs SHALL keep straight edges between node centers.

#### Scenario: Full-screen edges
- **WHEN** a user opens a full-screen Endpoint or Operation graph
- **THEN** every edge is a rounded step line between the facing sides of its two nodes

#### Scenario: Inline edges are unchanged
- **WHEN** the compact inline graph is shown
- **THEN** its edges are straight lines between node centers

### Requirement: Dependency graphs cap the drawn nodes and show a "more" node
A dependency graph SHALL NOT draw more than a fixed number of Service nodes: 6 in the compact inline graph and 50 in the full-screen graph, counted across publishers and subscribers together for Operations and across ordinary and expanded-group Services together when grouped. Group nodes SHALL NOT count toward the cap. When more linked Services exist than are drawn, the graph SHALL draw a "… +N more" node, where N is the number not drawn. In the compact graph, activating this node SHALL open the full-screen graph. In the full-screen graph, activating it SHALL close the full-screen view and navigate to the Linked Services tab of the same Endpoint or Operation, with the current search text pre-filled when a search is active; when the node belongs to an expanded group, the tab SHALL be narrowed to that group where the tab supports it, and otherwise by the group's name as search text.

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
- **WHEN** an Endpoint has 120 linked Services, grouping is off and the full-screen graph is open with the search box empty
- **THEN** 50 Service nodes and a "+70 more" node are drawn, and activating that node opens the Linked Services tab

#### Scenario: Full screen closes when the "more" node opens Linked Services
- **WHEN** a user activates the "more" node in the full-screen graph
- **THEN** the full-screen view closes and the Linked Services tab is shown

#### Scenario: Search text carries to Linked Services
- **WHEN** a search is active in the full-screen graph and the user activates the "more" node
- **THEN** the Linked Services tab opens with the same text in its search field

#### Scenario: Group nodes do not use the cap
- **WHEN** a grouped graph has 40 group nodes and no expanded group
- **THEN** all 40 group nodes are drawn and no "more" node appears

#### Scenario: The "more" node is not a Service
- **WHEN** a "more" node is drawn
- **THEN** it has no connection to the center node and activating it never navigates to a Service page

### Requirement: Full-screen graphs can be exported as an image
The full-screen view of both dependency graphs SHALL offer an Export control in its toolbar that opens a popup with a format choice (SVG or PNG), a "Transparent background" option and a "Grid" option, defaulting to SVG with both options on, and an Export action that downloads the graph as an image. The options SHALL reset to their defaults each time the popup opens and SHALL NOT be remembered. The image SHALL show the graph as currently framed, SHALL NOT include the zoom controls or the attribution, and SHALL omit the grid when "Grid" is off and use a white background when "Transparent background" is off. The compact inline graphs SHALL NOT offer an export.

#### Scenario: Default export
- **WHEN** a user opens Export in the full-screen graph and activates Export without changing anything
- **THEN** an SVG with a transparent background and the grid is downloaded

#### Scenario: PNG without transparency and grid
- **WHEN** a user chooses PNG, clears "Transparent background" and "Grid", and activates Export
- **THEN** a PNG with a white background and no grid is downloaded

#### Scenario: Options are not remembered
- **WHEN** a user exports a PNG and opens the Export popup again
- **THEN** SVG, "Transparent background" and "Grid" are selected again

#### Scenario: Inline graph has no export
- **WHEN** the compact inline graph is shown
- **THEN** it offers no Export control

