## MODIFIED Requirements

### Requirement: Visual Flow step authoring
The Flow create/edit page SHALL provide a Visual editor mode for its `steps` array, rendered as an interactive node canvas rather than a list of cards. The canvas SHALL allow an author to add, edit, retype, connect, reposition, and remove steps without editing JSON directly. Adding a step SHALL open a node-type picker offering Actor, Service, Data, API, System, Team, External, and Step; selecting an entity-backed type SHALL show a catalog lookup scoped to that type's kind, and selecting Step or External SHALL show fields for its own data (title, optional summary, and a semantic color for Step, or a label for External). Clicking an existing node SHALL reopen the same modal pre-filled with that step's current data, with a "Change type" action that resets type-specific fields. Connecting two nodes by dragging from one node's connection handle to another SHALL set the source step's `next_step` or append to its `next_steps`. The canvas SHALL preserve the persisted Flow `steps` JSON grammar and SHALL submit the same Flow API payload as the JSON editor.

#### Scenario: Add an entity-backed step from the node-type picker
- **WHEN** an author activates Add Step in Visual mode, selects the Service type, and chooses a Component from the catalog lookup
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

#### Scenario: Remove a node
- **WHEN** an author removes a node from the canvas
- **THEN** the editor removes transitions to that step's id and does not leave a transition targeting a nonexistent id

### Requirement: Catalog entity lookup for Flow steps
The node-type picker and edit modal SHALL provide a searchable catalog lookup for a step's `entity_ref`, scoped to the kind matching the selected node type (Actor → User, Team → Group, Service → Component, Data → Resource, API → API, System → System). The lookup SHALL store the selected entity's canonical `kind:name` reference. An author SHALL be able to clear the reference, which reverts the node to the plain Step type.

#### Scenario: Select a component reference
- **WHEN** an author selects the Service type and searches for and selects a Component in its entity lookup
- **THEN** the step stores that Component's canonical `component:name` reference and the node renders styled as a Service

#### Scenario: Clear a reference
- **WHEN** an author clears a step's entity lookup
- **THEN** the step's `entity_ref` is removed and the node reverts to the plain Step type

### Requirement: Visual editor structural feedback
The Visual editor SHALL report invalid step IDs and invalid transitions before save, and SHALL enforce structural rules at the moment an author attempts them on the canvas. It SHALL not allow a drag-to-connect gesture to complete a transition to an unknown step, a transition that gives a target more than one incoming edge, or a transition that introduces a cycle — the attempted connection SHALL be rejected with an inline explanation instead of being added. The editor SHALL block saving while any validation error is present (e.g. a duplicate step id entered in a node's edit modal).

#### Scenario: Attempt to reconverge branches
- **WHEN** an author drags a connection from one node to a step that is already targeted by another step's transition
- **THEN** the Visual editor rejects the connection and explains that Flow branches cannot reconverge

#### Scenario: Duplicate step id
- **WHEN** an author changes a node's id, in its edit modal, to an id already used by another step
- **THEN** the Visual editor highlights the duplicate id and prevents saving until it is unique

### Requirement: Synchronized Visual and JSON modes
The Flow edit page SHALL offer a compact Steps settings control that switches between Visual and JSON editor modes. Both modes SHALL represent the same in-memory steps data. Switching from Visual to JSON SHALL show formatted JSON for the current visual edits, including any `position`, `label_theme`, or `external_label` fields set on the canvas. Switching from JSON to Visual SHALL be allowed only when the JSON parses and satisfies the supported step schema; otherwise the JSON editor SHALL remain visible with an explanation and shall not discard the text. Steps that reach Visual mode without a stored `position` SHALL be placed by autolayout rather than left unplaced.

#### Scenario: Switch after visual edits
- **WHEN** an author edits a step title or transition in Visual mode and switches to JSON mode
- **THEN** the JSON editor displays those edits in the serialized `steps` array without requiring a save

#### Scenario: Invalid JSON prevents Visual mode
- **WHEN** an author tries to switch to Visual mode while the JSON is malformed or fails schema validation
- **THEN** the page remains in JSON mode, shows the validation issue, and retains the entered JSON text

#### Scenario: Steps without a stored position autolayout on entering Visual mode
- **WHEN** an author switches to Visual mode and one or more steps in the current JSON have no `position`
- **THEN** those steps are placed on the canvas by autolayout instead of stacking at a default coordinate
