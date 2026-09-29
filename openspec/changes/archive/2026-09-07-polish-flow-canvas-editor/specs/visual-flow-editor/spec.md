## MODIFIED Requirements

### Requirement: Synchronized Visual and JSON modes
The Flow edit page SHALL always show the interactive canvas as its primary, full-width view, and SHALL provide a control that opens or collapses a JSON rail panel alongside it. The canvas and the JSON rail SHALL represent the same in-memory steps data. Editing on the canvas SHALL update the JSON rail's content, when open, without requiring a save. Typing in the JSON rail SHALL update the canvas only when the JSON parses and satisfies the supported step schema; while the JSON is invalid, the canvas SHALL keep showing its last successfully-parsed state and the JSON rail SHALL show the validation issue inline without discarding the entered text. Steps that reach the canvas without a stored `position` SHALL be placed by autolayout rather than left unplaced.

#### Scenario: Canvas edits reflect in the open JSON rail
- **WHEN** an author edits a step title or transition on the canvas while the JSON rail is open
- **THEN** the JSON rail displays those edits in the serialized `steps` array without requiring a save

#### Scenario: Invalid JSON does not affect the canvas
- **WHEN** an author types JSON in the rail that is malformed or fails schema validation
- **THEN** the canvas keeps showing its last valid state, and the JSON rail shows the validation issue and retains the entered text

#### Scenario: Steps without a stored position autolayout on the canvas
- **WHEN** the canvas renders a set of steps and one or more have no `position`
- **THEN** those steps are placed on the canvas by autolayout instead of stacking at a default coordinate

### Requirement: Visual Flow step authoring

The Flow create/edit page SHALL provide the interactive node canvas as its primary way to author its `steps` array. The canvas SHALL allow an author to add, edit, retype, connect, reposition, remove, and — for a transition between two existing steps — edit or delete that transition independently of either endpoint step, all without editing JSON directly. Adding a step SHALL open a node-type picker offering Actor, Service, Data, API, System, Team, External, and Step; selecting an entity-backed type SHALL show a catalog lookup scoped to that type's kind, and selecting Step or External SHALL show fields for its own data (title, optional summary, and a semantic color for Step, or a label for External). Clicking an existing node SHALL reopen the same modal pre-filled with that step's current data, with a "Change type" action that resets type-specific fields. Connecting two nodes by dragging from one node's connection handle to another SHALL set the source step's `next_step` or append to its `next_steps`. Clicking an existing transition SHALL open a modal to edit its `label` or delete the transition, without removing either step it connects. The canvas SHALL preserve the persisted Flow `steps` JSON grammar and SHALL submit the same Flow API payload as the JSON editor.

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

#### Scenario: Edit a transition's label

- **WHEN** an author clicks an existing transition on the canvas and changes its label in the opened modal
- **THEN** the corresponding `next_step.label` or `next_steps[]` entry's `label` is updated and the new label renders on the connection

#### Scenario: Delete a transition without deleting either step

- **WHEN** an author clicks an existing transition on the canvas and activates Delete in the opened modal
- **THEN** the transition is removed from the source step's `next_step`/`next_steps`, the connection no longer renders, and both the source and target steps remain on the canvas

#### Scenario: Remove a node

- **WHEN** an author removes a node from the canvas
- **THEN** the editor removes transitions to that step's id and does not leave a transition targeting a nonexistent id
