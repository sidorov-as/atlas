## MODIFIED Requirements

### Requirement: Client-side Flow diagram and Flow authoring UI
A Flow's detail page SHALL render its `steps` as a typed, colored node diagram (see the Flow diagram nodes are typed and colored by kind requirement), computed and laid out entirely client-side from the `steps` data (independent of the catalog's C4 diagram endpoint). Wherever this diagram is rendered — including the read-only detail page and the edit page's canvas — it SHALL provide zoom-in, zoom-out, and fit-to-viewport controls. A transition's optional `label` (from `next_step.label` or a `next_steps[]` entry's `label`) SHALL be rendered on its corresponding connection in the diagram. The Flow edit page SHALL provide a JSON code editor over the `steps` array, with JSON syntax highlighting and inline schema validation, and a Visual editor mode (an interactive node canvas) for authoring the same steps data. The edit page SHALL provide a compact settings control for switching between these modes. The JSON editor and Visual editor SHALL remain synchronized without requiring a save. The edit page SHALL show a live preview that re-renders the diagram as either editor changes the steps. Clicking a step's node in the edit page's diagram SHALL select that step in the active editing mode. The edit page SHALL provide a control to add a new step in either mode, a control to collapse and expand the active editor panel, and a Markdown Documentation editor. The read-only detail page SHALL render the Flow's formatted Markdown documentation below the graph and Steps section.

#### Scenario: Detail page renders the diagram
- **WHEN** a user opens a Flow's detail page
- **THEN** its steps are rendered as a typed, colored node diagram reflecting each step's kind and transitions

#### Scenario: Transition labels render on connections
- **WHEN** a step's `next_step` or a `next_steps[]` entry has a non-empty `label`
- **THEN** that label is rendered on the corresponding connection in the diagram, on both the read-only detail page and the edit page's canvas

#### Scenario: Live preview updates as the JSON is edited
- **WHEN** a user edits the `steps` JSON in the edit page's editor
- **THEN** the diagram preview re-renders to reflect the edited steps without requiring a save

#### Scenario: Live preview updates from the Visual editor
- **WHEN** a user changes a step or transition in the edit page's Visual editor canvas
- **THEN** the diagram preview re-renders to reflect the change without requiring a save

#### Scenario: Invalid edits are rejected on save
- **WHEN** a user attempts to save `steps` JSON that fails entity-ref resolution or the strict-tree rule
- **THEN** the save is rejected and the user is shown the validation failure

#### Scenario: Malformed JSON is flagged inline
- **WHEN** a user types `steps` JSON that is not valid JSON or does not match the expected step shape
- **THEN** the editor highlights the error inline, before any save is attempted, without discarding the last successfully-parsed preview

#### Scenario: Diagram supports zoom and fit-to-viewport
- **WHEN** a user views a Flow's diagram, on either the detail page or the edit page
- **THEN** zoom-in, zoom-out, and fit-to-viewport controls are available and adjust the diagram's camera accordingly

#### Scenario: Clicking a diagram node selects the active editor
- **WHEN** a user clicks a step's node in the edit page's diagram
- **THEN** in JSON mode the JSON editor selects that step's JSON block; in Visual mode the canvas opens that step's edit modal

#### Scenario: A new step can be added from either editor
- **WHEN** a user activates the "Add Step" control on the edit page
- **THEN** in JSON mode a new step object with a fresh, non-colliding `id` is appended to the array and the JSON editor focuses it; in Visual mode a node-type picker opens, and once a type is chosen a new step with a fresh, non-colliding `id` is added to the canvas as an unconnected node and focused

#### Scenario: The active editor panel can be collapsed
- **WHEN** a user toggles the editor-panel control on the edit page
- **THEN** the active editor panel is hidden and the diagram preview expands to fill the available width, and toggling again restores the active editor panel

#### Scenario: Flow documentation follows the operational content
- **WHEN** a user opens a Flow with graph steps and Markdown documentation
- **THEN** the formatted documentation is rendered below the graph and Steps section

## ADDED Requirements

### Requirement: Flow diagram nodes are typed and colored by kind
Each step's node SHALL render styled according to its kind: a step whose `entity_ref` targets a `user` or `group` SHALL render as an Actor or Team node respectively, `component` as a Service node, `resource` as a Data node, `api` as an API node, and `system` as a System node, each using a fixed color drawn from the catalog's existing C4 diagram palette. A step with no `entity_ref` SHALL render as a plain Step node (optionally colored per its `label_theme`) unless it carries `external_label`, in which case it SHALL render as an External node using the catalog's fixed External color. This styling SHALL apply identically on the read-only detail page and the edit page's canvas.

#### Scenario: Component-backed step renders as a colored Service node
- **WHEN** a step's `entity_ref` resolves to a Component
- **THEN** the step's node renders with the Service node's fixed color and a Service type label

#### Scenario: Step without an entity_ref renders as a plain Step node
- **WHEN** a step has no `entity_ref` and no `external_label`
- **THEN** the step's node renders as a Step node, colored per its `label_theme` if set, or with a neutral default otherwise

#### Scenario: Step with an external_label renders as an External node
- **WHEN** a step has an `external_label` and no `entity_ref`
- **THEN** the step's node renders as an External node using the catalog's fixed External color

#### Scenario: Diagram styling matches between detail page and edit canvas
- **WHEN** the same Flow is viewed on its read-only detail page and on its edit page's canvas
- **THEN** corresponding steps render with identical node type and color on both

### Requirement: Flow diagram layout direction and manual node positioning
A step MAY carry an optional `position` (`{x, y}`). Wherever the diagram is rendered, a step with a stored `position` SHALL render at that position; a step without one SHALL be placed by an automatic layout pass. The edit page's canvas SHALL allow an author to drag a node to a new position, which SHALL update that step's `position`. The edit page SHALL provide an explicit "Auto layout" control that recomputes and overwrites every visible step's `position`, and a layout-direction setting (top-down or left-right) that determines the orientation Auto layout uses.

#### Scenario: A step with a stored position renders there
- **WHEN** a Flow is loaded and a step has a stored `position`
- **THEN** that step's node renders at the stored coordinates rather than at an autolayout-computed position

#### Scenario: A step without a stored position is autolaid-out
- **WHEN** a Flow is loaded and a step has no stored `position`
- **THEN** that step's node is placed by the automatic layout pass

#### Scenario: Dragging a node persists its new position
- **WHEN** an author drags a node to a new location on the edit page's canvas
- **THEN** that step's `position` is updated to the new coordinates in the in-memory steps data

#### Scenario: Auto layout recomputes every position
- **WHEN** an author activates the Auto layout control
- **THEN** every step's `position` is recomputed according to the current layout-direction setting and the canvas re-renders accordingly

#### Scenario: Changing layout direction affects Auto layout
- **WHEN** an author changes the layout-direction setting from left-right to top-down and activates Auto layout
- **THEN** the recomputed positions arrange steps top-down instead of left-right

### Requirement: Step supports non-entity Step and External kinds
A step MAY carry a `label_theme` (one of the values `success`, `danger`, `warning`, `info`, `utility`, or `normal`) when it has no `entity_ref`, used only to color its Step node. A step MAY instead carry an `external_label` (a free-text string) when it has no `entity_ref`, identifying it as an External node. A step SHALL NOT carry both `entity_ref` and `external_label`; on save, a step violating this SHALL be rejected.

#### Scenario: A Step node's label_theme is saved and rendered
- **WHEN** a Flow is saved with a step that has no `entity_ref` and a `label_theme` of `success`
- **THEN** the Flow is persisted with that value and the step's node renders in the corresponding color

#### Scenario: An External node's label is saved and rendered
- **WHEN** a Flow is saved with a step that has no `entity_ref` and an `external_label` of "Payment Gateway"
- **THEN** the Flow is persisted with that value and the step's node renders as External showing that label

#### Scenario: entity_ref and external_label are mutually exclusive
- **WHEN** a Flow is saved with a step that has both a non-empty `entity_ref` and a non-empty `external_label`
- **THEN** the save is rejected
