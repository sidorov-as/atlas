## MODIFIED Requirements

### Requirement: Flow detail page renders and edits the step diagram
A Flow's detail page SHALL render its `steps` as a left-to-right tree diagram, computed and laid out entirely client-side from the `steps` data (independent of the catalog's C4 diagram endpoint). Wherever this diagram is rendered — including the read-only detail page and the edit page's live preview — it SHALL provide zoom-in, zoom-out, and fit-to-viewport controls. A transition's optional `label` (from `next_step.label` or a `next_steps[]` entry's `label`) SHALL be rendered on its corresponding connection in the diagram. The Flow edit page SHALL provide a code editor over the `steps` array, with JSON syntax highlighting and inline schema validation, with a live preview that re-renders the diagram as the JSON is edited, and SHALL allow saving changes. Clicking a step's node in the edit page's diagram SHALL scroll the code editor to and select that step's corresponding JSON block. The edit page SHALL provide a control to append a new, unconnected step to the `steps` JSON, and a control to collapse and expand the code editor panel.

#### Scenario: Detail page renders the diagram
- **WHEN** a user opens a Flow's detail page
- **THEN** its steps are rendered as a left-to-right tree diagram reflecting each step's transitions

#### Scenario: Transition labels render on connections
- **WHEN** a step's `next_step` or a `next_steps[]` entry has a non-empty `label`
- **THEN** that label is rendered on the corresponding connection in the diagram, on both the read-only detail page and the edit page's live preview

#### Scenario: Live preview updates as the JSON is edited
- **WHEN** a user edits the `steps` JSON in the edit page's editor
- **THEN** the diagram preview re-renders to reflect the edited steps without requiring a save

#### Scenario: Invalid edits are rejected on save
- **WHEN** a user attempts to save `steps` JSON that fails entity-ref resolution or the strict-tree rule
- **THEN** the save is rejected and the user is shown the validation failure

#### Scenario: Malformed JSON is flagged inline
- **WHEN** a user types `steps` JSON that is not valid JSON or does not match the expected step shape
- **THEN** the editor highlights the error inline, before any save is attempted, without discarding the last successfully-parsed preview

#### Scenario: Diagram supports zoom and fit-to-viewport
- **WHEN** a user views a Flow's diagram, on either the detail page or the edit page
- **THEN** zoom-in, zoom-out, and fit-to-viewport controls are available and adjust the diagram's camera accordingly

#### Scenario: Clicking a diagram node navigates to its JSON
- **WHEN** a user clicks a step's node in the edit page's diagram
- **THEN** the code editor scrolls to and selects that step's corresponding block in the `steps` JSON

#### Scenario: A new step can be added from the editor
- **WHEN** a user activates the "Add Step" control on the edit page
- **THEN** a new step object with a fresh, non-colliding `id` is appended to the `steps` JSON, the diagram preview shows it as an unconnected node, and the editor scrolls to the new step's JSON block
