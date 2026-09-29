## MODIFIED Requirements

### Requirement: Client-side Flow diagram and Flow authoring UI
A Flow's detail page SHALL render its `steps` as a typed, colored node diagram (see the Flow diagram nodes are typed and colored by kind requirement), computed and laid out entirely client-side from the `steps` data (independent of the catalog's C4 diagram endpoint). Wherever this diagram is rendered — including the read-only detail page and the edit page's canvas — it SHALL provide zoom-in, zoom-out, and fit-to-viewport controls. A transition's optional `label` (from `next_step.label` or a `next_steps[]` entry's `label`) SHALL be rendered on its corresponding connection in the diagram, alongside a directional arrowhead indicating which step the transition leads to. The Flow edit page's diagram SHALL be the same interactive canvas an author edits on — adding, editing, retyping, connecting, repositioning, and removing steps directly on it — with no separate, non-interactive preview rendering the same steps a second time. The edit page SHALL provide a JSON code editor over the `steps` array, with JSON syntax highlighting and inline schema validation, available in a collapsible panel alongside the canvas; the two SHALL remain synchronized without requiring a save, in both directions. The edit page SHALL provide a control to add a new step directly on the canvas, a control to collapse and expand the JSON panel, and a Markdown Documentation editor. The read-only detail page SHALL render the Flow's formatted Markdown documentation below the graph and Steps section.

#### Scenario: Detail page renders the diagram
- **WHEN** a user opens a Flow's detail page
- **THEN** its steps are rendered as a typed, colored node diagram reflecting each step's kind and transitions

#### Scenario: Transition labels and direction render on connections
- **WHEN** a step's `next_step` or a `next_steps[]` entry has a non-empty `label`
- **THEN** that label is rendered on the corresponding connection in the diagram, with a directional arrowhead, on both the read-only detail page and the edit page's canvas

#### Scenario: The canvas updates as JSON is edited
- **WHEN** a user edits the `steps` JSON in the edit page's JSON panel
- **THEN** the canvas re-renders to reflect the edited steps without requiring a save

#### Scenario: The JSON panel updates from the canvas
- **WHEN** a user changes a step or transition directly on the edit page's canvas
- **THEN** the JSON panel, if open, re-renders to reflect the change without requiring a save

#### Scenario: Invalid edits are rejected on save
- **WHEN** a user attempts to save `steps` JSON that fails entity-ref resolution or the strict-tree rule
- **THEN** the save is rejected and the user is shown the validation failure

#### Scenario: Malformed JSON is flagged inline
- **WHEN** a user types `steps` JSON that is not valid JSON or does not match the expected step shape
- **THEN** the editor highlights the error inline, before any save is attempted, without discarding the last successfully-parsed canvas state

#### Scenario: Diagram supports zoom and fit-to-viewport
- **WHEN** a user views a Flow's diagram, on either the detail page or the edit page
- **THEN** zoom-in, zoom-out, and fit-to-viewport controls are available and adjust the diagram's camera accordingly

#### Scenario: Clicking a diagram node opens its edit modal
- **WHEN** a user clicks a step's node on the edit page's canvas
- **THEN** that step's edit modal opens; if the JSON panel is also open, it additionally scrolls to and selects that step's JSON block

#### Scenario: A new step can be added from the canvas
- **WHEN** a user activates the "Add Step" control on the edit page
- **THEN** a node-type picker opens, and once a type is chosen a new step with a fresh, non-colliding `id` is added to the canvas as an unconnected node and focused

#### Scenario: The JSON panel can be collapsed
- **WHEN** a user toggles the JSON-panel control on the edit page
- **THEN** the JSON panel is hidden and the canvas expands to fill the available width, and toggling again restores the JSON panel

#### Scenario: Flow documentation follows the operational content
- **WHEN** a user opens a Flow with graph steps and Markdown documentation
- **THEN** the formatted documentation is rendered below the graph and Steps section

### Requirement: Flow diagram nodes are typed and colored by kind
Each step's node SHALL render styled according to its kind: a step whose `entity_ref` targets a `user` or `group` SHALL render as an Actor or Team node respectively, `component` as a Service node, `resource` as a Data node, `api` as an API node, and `system` as a System node, each using a fixed color drawn from the catalog's existing C4 diagram palette, alongside an icon and a kind label visually distinguished from the node's own title text. A step with no `entity_ref` SHALL render as a plain Step node (optionally colored per its `label_theme`) unless it carries `external_label`, in which case it SHALL render as an External node using the catalog's fixed External color. A node's title, subtitle, and kind label SHALL show their full value in a tooltip when hovered, regardless of whether the displayed text is visually truncated. This styling SHALL apply identically on the read-only detail page and the edit page's canvas.

#### Scenario: Component-backed step renders as a colored Service node
- **WHEN** a step's `entity_ref` resolves to a Component
- **THEN** the step's node renders with the Service node's fixed color, a Service icon, and a Service type label visually distinct from the node's title

#### Scenario: Step without an entity_ref renders as a plain Step node
- **WHEN** a step has no `entity_ref` and no `external_label`
- **THEN** the step's node renders as a Step node, colored per its `label_theme` if set, or with a neutral default otherwise

#### Scenario: Step with an external_label renders as an External node
- **WHEN** a step has an `external_label` and no `entity_ref`
- **THEN** the step's node renders as an External node using the catalog's fixed External color

#### Scenario: Diagram styling matches between detail page and edit canvas
- **WHEN** the same Flow is viewed on its read-only detail page and on its edit page's canvas
- **THEN** corresponding steps render with identical node type, color, and icon on both

#### Scenario: Hovering truncated node text shows its full value
- **WHEN** a user hovers a node whose title or subtitle is too long to display in full
- **THEN** a tooltip shows the complete, untruncated text

### Requirement: Flow diagram layout direction and manual node positioning
A step MAY carry an optional `position` (`{x, y}`). Wherever the diagram is rendered, a step with a stored `position` SHALL render at that position; a step without one SHALL be placed by an automatic layout pass, with enough spacing between sibling nodes in the same layer that adjacent node borders do not touch. The edit page's canvas SHALL allow an author to drag a node to a new position, which SHALL update that step's `position`. The edit page SHALL provide an explicit "Auto layout" control that recomputes and overwrites every visible step's `position`, and a layout-direction setting (top-down or left-right) that determines the orientation Auto layout uses. Changing the layout-direction setting SHALL itself immediately recompute and overwrite every visible step's `position` using the new direction, without requiring the author to separately activate Auto layout.

#### Scenario: A step with a stored position renders there
- **WHEN** a Flow is loaded and a step has a stored `position`
- **THEN** that step's node renders at the stored coordinates rather than at an autolayout-computed position

#### Scenario: A step without a stored position is autolaid-out
- **WHEN** a Flow is loaded and a step has no stored `position`
- **THEN** that step's node is placed by the automatic layout pass, with visible spacing from its siblings

#### Scenario: Dragging a node persists its new position
- **WHEN** an author drags a node to a new location on the edit page's canvas
- **THEN** that step's `position` is updated to the new coordinates in the in-memory steps data

#### Scenario: Auto layout recomputes every position
- **WHEN** an author activates the Auto layout control
- **THEN** every step's `position` is recomputed according to the current layout-direction setting and the canvas re-renders accordingly

#### Scenario: Changing the layout-direction setting immediately re-lays out the canvas
- **WHEN** an author changes the layout-direction setting from left-right to top-down
- **THEN** every visible step's `position` is immediately recomputed and the canvas re-renders arranged top-down, without a separate Auto layout activation
