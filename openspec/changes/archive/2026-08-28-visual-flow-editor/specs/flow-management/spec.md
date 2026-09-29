## MODIFIED Requirements

### Requirement: Client-side Flow diagram and Flow authoring UI
A Flow's detail page SHALL render its `steps` as a left-to-right tree diagram, computed and laid out entirely client-side from the `steps` data (independent of the catalog's C4 diagram endpoint). Wherever this diagram is rendered — including the read-only detail page and the edit page's live preview — it SHALL provide zoom-in, zoom-out, and fit-to-viewport controls. A transition's optional `label` (from `next_step.label` or a `next_steps[]` entry's `label`) SHALL be rendered on its corresponding connection in the diagram. The Flow edit page SHALL provide a JSON code editor over the `steps` array, with JSON syntax highlighting and inline schema validation, and a Visual editor mode for authoring the same steps data. The edit page SHALL provide a compact settings control for switching between these modes. The JSON editor and Visual editor SHALL remain synchronized without requiring a save. The edit page SHALL show a live preview that re-renders the diagram as either editor changes the steps. Clicking a step's node in the edit page's diagram SHALL select that step in the active editing mode. The edit page SHALL provide a control to append a new, unconnected step in either mode, a control to collapse and expand the active editor panel, and a Markdown Documentation editor. The read-only detail page SHALL render the Flow's formatted Markdown documentation below the graph and Steps section.

#### Scenario: Render a Flow diagram
- **WHEN** a user opens a Flow's detail page
- **THEN** its steps are rendered as a left-to-right tree diagram reflecting each step's transitions

#### Scenario: Render a transition label
- **WHEN** a step's `next_step` or a `next_steps[]` entry has a non-empty `label`
- **THEN** that label is rendered on the corresponding connection in the diagram, on both the read-only detail page and the edit page's live preview

#### Scenario: Update preview from JSON
- **WHEN** a user edits the `steps` JSON in the edit page's JSON editor
- **THEN** the diagram preview re-renders to reflect the edited steps without requiring a save

#### Scenario: Update preview from the Visual editor
- **WHEN** a user changes a step or transition in the edit page's Visual editor
- **THEN** the diagram preview re-renders to reflect the change without requiring a save

#### Scenario: Reject invalid Flow data on save
- **WHEN** a user attempts to save steps that fail entity-ref resolution or the strict-tree rule
- **THEN** the save is rejected and the user is shown the validation failure

#### Scenario: Highlight invalid JSON before save
- **WHEN** a user types `steps` JSON that is not valid JSON or does not match the expected step shape
- **THEN** the JSON editor highlights the error inline, before any save is attempted, without discarding the last successfully-parsed preview

#### Scenario: Control the diagram camera
- **WHEN** a user views a Flow's diagram, on either the detail page or the edit page
- **THEN** zoom-in, zoom-out, and fit-to-viewport controls are available and adjust the diagram's camera accordingly

#### Scenario: Select a step from the graph
- **WHEN** a user clicks a step's node in the edit page's diagram
- **THEN** the active editor focuses the corresponding step, selecting its JSON block in JSON mode or its visual card in Visual mode

#### Scenario: Add a step in either mode
- **WHEN** a user activates the Add Step control on the edit page
- **THEN** a new step object with a fresh, non-colliding id is added, the diagram preview shows it as an unconnected node, and the active editor focuses the new step

#### Scenario: Collapse the active editor
- **WHEN** a user toggles the editor-panel control on the edit page
- **THEN** the active editor panel is hidden and the diagram preview expands to fill the available width, and toggling again restores the active editor panel

#### Scenario: Render documentation
- **WHEN** a user opens a Flow with graph steps and Markdown documentation
- **THEN** the formatted documentation is rendered below the graph and Steps section
