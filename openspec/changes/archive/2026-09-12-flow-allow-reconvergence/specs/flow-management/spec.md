## REMOVED Requirements

### Requirement: Step transitions form a strict divergence-only tree
**Reason**: The tree-only constraint existed so the canvas could ship without a layered-layout library; ELK (which natively supports multiple incoming edges per node) was adopted for layout shortly after, so the constraint no longer serves a technical purpose. Authors documenting a process where two branches genuinely lead to the same outcome (e.g. two condition branches both reaching one "Success" step, or two code paths emitting the same downstream event) previously had to duplicate the target step per branch.
**Migration**: No data migration needed — every currently-persisted Flow already satisfies the new, looser rule (see the replacement requirement below), since a tree is a special case of a DAG. No author action is required.

## ADDED Requirements

### Requirement: Step transitions form an acyclic transition graph
Each step MAY declare a transition to the next step(s) via `next_step` (a single `{id, label}`) or `next_steps` (an array of `{id, label}` for branching). A step id MAY be the target of any number of incoming transitions — branches MAY both diverge and reconverge on a shared step. A transition MUST NOT target a step id that does not exist elsewhere in the same `steps` array, and the transitions across a Flow's `steps` array MUST NOT form a cycle (including a step transitioning to itself). A save that would violate either of these SHALL be rejected.

#### Scenario: Reconverging branches save successfully
- **WHEN** a Flow is saved where two different steps each declare a transition targeting the same step id
- **THEN** the Flow is persisted, and the target step is rendered with an incoming connection from each of those steps

#### Scenario: A transition to a nonexistent step id is rejected
- **WHEN** a Flow is saved where a `next_step`/`next_steps` entry targets a step id that does not exist elsewhere in the same `steps` array
- **THEN** the save is rejected

#### Scenario: A cycle is rejected
- **WHEN** a Flow is saved where following transitions from some step eventually leads back to that same step, whether directly (`next_step`/`next_steps` targeting itself) or through one or more intermediate steps
- **THEN** the save is rejected

## MODIFIED Requirements

### Requirement: Client-side Flow diagram and Flow authoring UI
A Flow's detail page SHALL render its `steps` as a typed, colored node diagram (see the Flow diagram nodes are typed and colored by kind requirement), computed and laid out entirely client-side from the `steps` data (independent of the catalog's C4 diagram endpoint). Wherever this diagram is rendered — including the read-only detail page and the edit page's canvas — it SHALL provide zoom-in, zoom-out, and fit-to-viewport controls. A transition's optional `label` (from `next_step.label` or a `next_steps[]` entry's `label`) SHALL be rendered on its corresponding connection in the diagram, alongside a directional arrowhead indicating which step the transition leads to, wrapping onto multiple lines within a fixed-width box rather than overflowing when the label is long. The Flow edit page's diagram SHALL be the same interactive canvas an author edits on — adding, editing, retyping, connecting, repositioning, and removing steps directly on it — with no separate, non-interactive preview rendering the same steps a second time. The edit page SHALL provide a JSON code editor over the `steps` array, with JSON syntax highlighting and inline schema validation, available in a collapsible panel alongside the canvas; the two SHALL remain synchronized without requiring a save, in both directions. The edit page SHALL provide a control to add a new unconnected step directly on the canvas, positioned so it never overlaps an existing step, a control to collapse and expand the JSON panel, and a Markdown Documentation editor. The read-only detail page SHALL render the Flow's formatted Markdown documentation below the graph and Steps section.

#### Scenario: Detail page renders the diagram
- **WHEN** a user opens a Flow's detail page
- **THEN** its steps are rendered as a typed, colored node diagram reflecting each step's kind and transitions

#### Scenario: Transition labels and direction render on connections
- **WHEN** a step's `next_step` or a `next_steps[]` entry has a non-empty `label`
- **THEN** that label is rendered on the corresponding connection in the diagram, with a directional arrowhead, on both the read-only detail page and the edit page's canvas

#### Scenario: Long transition labels wrap instead of overflowing
- **WHEN** a step's transition `label` is too long to fit on one line at the diagram's default label width
- **THEN** the label wraps onto multiple lines within a fixed-width box, on both the read-only detail page and the edit page's canvas, instead of rendering past the box or being cut off

#### Scenario: The canvas updates as JSON is edited
- **WHEN** a user edits the `steps` JSON in the edit page's JSON panel
- **THEN** the canvas re-renders to reflect the edited steps without requiring a save

#### Scenario: The JSON panel updates from the canvas
- **WHEN** a user changes a step or transition directly on the edit page's canvas
- **THEN** the JSON panel, if open, re-renders to reflect the change without requiring a save

#### Scenario: Invalid edits are rejected on save
- **WHEN** a user attempts to save `steps` JSON that fails entity-ref resolution, targets an unknown step id, or introduces a cycle
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

#### Scenario: An unconnected step can be added from the toolbar without overlapping existing steps
- **WHEN** a user activates the "Add Step" control on the edit page
- **THEN** a node-type picker opens, and once a type is chosen a new step with a fresh, non-colliding `id` is added to the canvas as an unconnected node, positioned below the diagram's existing steps so it does not overlap any of them, and the canvas fits to viewport to show it

#### Scenario: A step can be added and connected directly from an existing node
- **WHEN** a user activates a node's own add control on the edit page's canvas
- **THEN** a node-type picker opens, and once a type is chosen a new step with a fresh, non-colliding `id` is added as that node's outgoing transition (a new branch if it already has one) and positioned adjacent to it, without a separate drag-to-connect step

#### Scenario: A step with no outgoing transition offers an add-next placeholder
- **WHEN** a user views a step on the edit page's canvas that has no outgoing transition
- **THEN** a placeholder control is shown in the slot its next step would occupy, and activating it opens the same node-type picker and, once a type is chosen, adds and connects a new step exactly as that node's own add control would

#### Scenario: A step with an outgoing transition shows no add-next placeholder
- **WHEN** a user views a step on the edit page's canvas that already has a `next_step` or at least one `next_steps[]` entry
- **THEN** no add-next placeholder is shown for it; adding another branch from it is done via that node's own add control

#### Scenario: The JSON panel can be collapsed
- **WHEN** a user toggles the JSON-panel control on the edit page
- **THEN** the JSON panel is hidden and the canvas expands to fill the available width, and toggling again restores the JSON panel

#### Scenario: Flow documentation follows the operational content
- **WHEN** a user opens a Flow with graph steps and Markdown documentation
- **THEN** the formatted documentation is rendered below the graph and Steps section
