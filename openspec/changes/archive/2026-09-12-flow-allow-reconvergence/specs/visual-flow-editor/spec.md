## MODIFIED Requirements

### Requirement: Visual editor structural feedback

The Visual editor SHALL report invalid step IDs and invalid transitions before save, and SHALL enforce structural rules at the moment an author attempts them on the canvas. It SHALL not allow a drag-to-connect gesture to complete a transition to an unknown step or a transition that introduces a cycle — the attempted connection SHALL be rejected with an inline explanation instead of being added. A drag-to-connect gesture to a step that already has one or more incoming transitions SHALL be allowed, adding another incoming connection to that step. The editor SHALL block saving while any validation error is present. A step's `id` is not an editable field anywhere in the node-type picker or edit modal (see "Step id is not a visual-editor field"); a duplicate id, or any other structural error, can therefore only be introduced by hand-editing the JSON rail, where it is caught live by the "Synchronized Visual and JSON modes" requirement's structural-validity gate rather than surfacing only at save.

#### Scenario: Reconverging a connection is allowed

- **WHEN** an author drags a connection from one node to a step that is already targeted by another step's transition
- **THEN** the Visual editor adds the connection, and the target step's node shows an incoming connection from each source step

#### Scenario: A structurally invalid Flow cannot be saved

- **WHEN** an author attempts to save a Flow whose steps (however produced) fail structural validation — for example, two steps sharing the same id
- **THEN** the save is blocked with an inline explanation of the error, as a backstop independent of how the invalid state was reached

### Requirement: Synchronized Visual and JSON modes

The Flow edit page SHALL always show the interactive canvas as its primary, full-width view, and SHALL provide a control that opens or collapses a JSON rail panel alongside it. The JSON rail SHALL be collapsed by default when the Flow edit page loads. The canvas and the JSON rail SHALL represent the same in-memory steps data. Editing on the canvas SHALL update the JSON rail's content, when open, without requiring a save. Typing in the JSON rail SHALL update the canvas only when the JSON both parses and satisfies the supported step schema, AND the resulting steps pass structural validation (unique step ids, every transition target resolves to an existing step, no cycle) — evaluated against the freshly-typed candidate, not the canvas's already-committed state. While the JSON fails either check, the canvas SHALL keep showing its last successfully-parsed-and-valid state, and the JSON rail SHALL show the specific validation issue inline without discarding the entered text. Steps that reach the canvas without a stored `position` SHALL be placed by autolayout rather than left unplaced.

#### Scenario: JSON rail is collapsed when the Flow edit page loads

- **WHEN** an author opens the Flow edit page
- **THEN** the JSON rail is not shown by default, and the canvas occupies the full-width primary view until the author explicitly opens the rail

#### Scenario: Canvas edits reflect in the open JSON rail

- **WHEN** an author edits a step title or transition on the canvas while the JSON rail is open
- **THEN** the JSON rail displays those edits in the serialized `steps` array without requiring a save

#### Scenario: Invalid JSON does not affect the canvas

- **WHEN** an author types JSON in the rail that is malformed or fails schema validation
- **THEN** the canvas keeps showing its last valid state, and the JSON rail shows the validation issue and retains the entered text

#### Scenario: A structurally-broken JSON edit does not reach the canvas

- **WHEN** an author edits a step's `id` in the JSON rail without updating another step's `next_step`/`next_steps` that targeted the old id, so the edited JSON parses and satisfies the step schema but now transitions to an unknown step id
- **THEN** the canvas keeps showing its last valid state — it does not render the dangling transition — and the JSON rail shows the structural error inline, retaining the entered text

#### Scenario: A reconverging JSON edit reaches the canvas

- **WHEN** an author edits the JSON rail so that two different steps each transition to the same target step id, and the edit otherwise parses and satisfies the step schema
- **THEN** the canvas updates to show the target step with an incoming connection from each of those steps, without any structural error

#### Scenario: Steps without a stored position autolayout on the canvas

- **WHEN** the canvas renders a set of steps and one or more have no `position`
- **THEN** those steps are placed on the canvas by autolayout instead of stacking at a default coordinate
