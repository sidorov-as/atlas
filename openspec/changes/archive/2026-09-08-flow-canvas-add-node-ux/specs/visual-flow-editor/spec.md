## MODIFIED Requirements

### Requirement: Visual Flow step authoring

The Flow create/edit page SHALL provide the interactive node canvas as its primary way to author its `steps` array. The canvas SHALL allow an author to add, edit, retype, connect, reposition, remove, and — for a transition between two existing steps — edit or delete that transition independently of either endpoint step, all without editing JSON directly. Adding a step SHALL open a node-type picker offering Actor, Service, Data, API, System, Team, External, and Step; selecting an entity-backed type SHALL show a catalog lookup scoped to that type's kind, and selecting Step or External SHALL show fields for its own data (title, optional summary, and a semantic color for Step, or a label for External). Clicking an existing node SHALL reopen the same modal pre-filled with that step's current data, with a "Change type" action that resets type-specific fields. Connecting two nodes by dragging from one node's connection handle to another SHALL set the source step's `next_step` or append to its `next_steps`. An author SHALL additionally be able to open the same node-type picker directly from an existing node — via that node's own add control, or via a placeholder shown only next to a step with no outgoing transition — and once a type is chosen, the new step SHALL be connected as that node's `next_step` (or appended to its `next_steps` if it already has one) and positioned adjacent to it, without requiring a separate drag-to-connect gesture. Every node's add and remove controls on the canvas SHALL remain visible at all times, not only while the node is hovered. Clicking an existing transition SHALL open a modal to edit its `label` or delete the transition, without removing either step it connects. The canvas SHALL preserve the persisted Flow `steps` JSON grammar and SHALL submit the same Flow API payload as the JSON editor.

#### Scenario: Add an entity-backed step from the node-type picker

- **WHEN** an author activates Add Step, selects the Service type, and chooses a Component from the catalog lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Service, and referencing the selected Component's canonical `component:name` ref

#### Scenario: Add a plain Step node with a semantic color

- **WHEN** an author activates Add Step, selects the Step type, and chooses the "danger" color
- **THEN** a new node is added styled with the danger color and no `entity_ref`

#### Scenario: Add an External node

- **WHEN** an author activates Add Step, selects the External type, and enters a label
- **THEN** a new node is added styled as External, storing that label and no `entity_ref`

#### Scenario: Retype an existing node

- **WHEN** an author clicks an existing Service node, activates "Change type", and selects Data, then chooses a Resource from the catalog lookup
- **THEN** the step's `entity_ref` is replaced with the selected Resource's reference and the node re-renders styled as Data

#### Scenario: Connect two nodes by dragging

- **WHEN** an author drags from one node's connection handle and drops it on another node
- **THEN** the source step's transition is updated to target the dropped-on step, and the canvas renders a connection between them

#### Scenario: Add a step directly from an existing node's own add control

- **WHEN** an author activates a node's own add control, selects a type, and completes the node-type picker
- **THEN** the new step is connected as that node's `next_step` (or appended to `next_steps` if it already has one) and positioned adjacent to it on the canvas, with no separate drag-to-connect gesture needed

#### Scenario: Add a step from a childless step's add-next placeholder

- **WHEN** an author activates the add-next placeholder shown next to a step with no outgoing transition, and completes the node-type picker
- **THEN** the new step is connected and positioned exactly as activating that step's own add control would, and the placeholder no longer renders for that step once it has an outgoing transition

#### Scenario: Node add and remove controls remain visible without hovering

- **WHEN** an author views the canvas without hovering any node
- **THEN** every node's add and remove controls are visible, not only the node currently under the pointer

#### Scenario: Edit a transition's label

- **WHEN** an author clicks an existing transition on the canvas and changes its label in the opened modal
- **THEN** the corresponding `next_step.label` or `next_steps[]` entry's `label` is updated and the new label renders on the connection

#### Scenario: Delete a transition without deleting either step

- **WHEN** an author clicks an existing transition on the canvas and activates Delete in the opened modal
- **THEN** the transition is removed from the source step's `next_step`/`next_steps`, the connection no longer renders, and both the source and target steps remain on the canvas

#### Scenario: Remove a node

- **WHEN** an author removes a node from the canvas
- **THEN** the editor removes transitions to that step's id and does not leave a transition targeting a nonexistent id
