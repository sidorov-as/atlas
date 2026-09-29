## ADDED Requirements

### Requirement: Visual Flow step authoring
The Flow create/edit page SHALL provide a Visual editor mode for its `steps` array. The mode SHALL render each step as an editable card and SHALL allow an author to add, edit, remove, and reorder steps without editing JSON directly. Each card SHALL support the step's `id`, `title`, optional `summary`, optional `entity_ref`, and its outgoing transition or transitions. The Visual editor SHALL preserve the persisted Flow `steps` JSON grammar and SHALL submit the same Flow API payload as the JSON editor.

#### Scenario: Add an unconnected step visually
- **WHEN** an author activates Add Step in Visual mode
- **THEN** the editor adds and focuses a step with a fresh non-colliding id, a default title, and no outgoing transition

#### Scenario: Edit a branched step visually
- **WHEN** an author configures two labelled outgoing branch rows for a step in Visual mode
- **THEN** the submitted `steps` array represents those rows as `next_steps` entries with their selected target ids and labels

#### Scenario: Remove a step
- **WHEN** an author removes a step in Visual mode
- **THEN** the editor removes transitions to that step and does not leave a transition targeting a nonexistent id

### Requirement: Catalog entity lookup for Flow steps
The Visual editor SHALL provide a searchable, grouped catalog lookup for a step's optional `entity_ref`. The lookup SHALL display each result's entity kind and SHALL store the selected entity's canonical `kind:name` reference. An author SHALL be able to clear the reference.

#### Scenario: Select a component reference
- **WHEN** an author searches for and selects a Component in a step's entity lookup
- **THEN** the step stores that Component's canonical `component:name` reference and the selected kind remains visible in the control

#### Scenario: Clear a reference
- **WHEN** an author clears a step's entity lookup
- **THEN** the step is saved without an `entity_ref`

### Requirement: Visual editor structural feedback
The Visual editor SHALL report invalid step IDs and invalid transitions before save. It SHALL not allow a user to create a transition to an unknown step, a transition that gives a target more than one incoming edge, or a transition that introduces a cycle. The editor SHALL block saving while such a validation error is present.

#### Scenario: Attempt to reconverge branches
- **WHEN** an author selects a target step that is already targeted by another step
- **THEN** the Visual editor rejects the selection and explains that Flow branches cannot reconverge

#### Scenario: Duplicate step id
- **WHEN** an author changes a visual step's id to an id already used by another step
- **THEN** the Visual editor highlights the duplicate id and prevents saving until it is unique

### Requirement: Synchronized Visual and JSON modes
The Flow edit page SHALL offer a compact Steps settings control that switches between Visual and JSON editor modes. Both modes SHALL represent the same in-memory steps data. Switching from Visual to JSON SHALL show formatted JSON for the current visual edits. Switching from JSON to Visual SHALL be allowed only when the JSON parses and satisfies the supported step schema; otherwise the JSON editor SHALL remain visible with an explanation and shall not discard the text.

#### Scenario: Switch after visual edits
- **WHEN** an author edits a step title or transition in Visual mode and switches to JSON mode
- **THEN** the JSON editor displays those edits in the serialized `steps` array without requiring a save

#### Scenario: Invalid JSON prevents Visual mode
- **WHEN** an author tries to switch to Visual mode while the JSON is malformed or fails schema validation
- **THEN** the page remains in JSON mode, shows the validation issue, and retains the entered JSON text

