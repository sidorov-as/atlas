## MODIFIED Requirements

### Requirement: Client-side Flow diagram and Flow authoring UI
A Flow's detail page SHALL render its `steps` as a typed, colored node diagram (see the Flow diagram nodes are typed and colored by kind requirement), computed and laid out entirely client-side from the `steps` data (independent of the catalog's C4 diagram endpoint). Wherever this diagram is rendered — including the read-only detail page and the edit page's canvas — it SHALL provide zoom-in, zoom-out, and fit-to-viewport controls. A transition's optional `label` (from `next_step.label` or a `next_steps[]` entry's `label`) SHALL be rendered on its corresponding connection in the diagram, alongside a directional arrowhead indicating which step the transition leads to, in a box that grows to fit the label up to a maximum size and clamps with an ellipsis past that size, making the full label available via a tooltip, rather than overflowing when the label is long. Clicking a connection's label SHALL open its transition-edit modal, the same as clicking anywhere else along the connection. Each connection SHALL render as a direct curve between its two endpoint steps' current positions, computed fresh at render time; no connection's rendered path is persisted or retained independently of its endpoint steps' positions — a `steps` change, an `autolayout_enabled` toggle, or the manual layout control never leaves a connection rendering a stale or previously-computed path. The Flow edit page's diagram SHALL be the same interactive canvas an author edits on — adding, editing, retyping, connecting, repositioning, and removing steps directly on it — with no separate, non-interactive preview rendering the same steps a second time. The edit page SHALL provide a JSON code editor over the `steps` array, with JSON syntax highlighting and inline schema validation, available in a collapsible panel alongside the canvas; the two SHALL remain synchronized without requiring a save, in both directions. The edit page SHALL provide a control to add a new unconnected step directly on the canvas, positioned so it never overlaps an existing step, a control to collapse and expand the JSON panel, and a Markdown Documentation editor. The read-only detail page SHALL render the Flow's formatted Markdown documentation below the graph and Steps section.

#### Scenario: Detail page renders the diagram
- **WHEN** a user opens a Flow's detail page
- **THEN** its steps are rendered as a typed, colored node diagram reflecting each step's kind and transitions

#### Scenario: Transition labels and direction render on connections
- **WHEN** a step's `next_step` or a `next_steps[]` entry has a non-empty `label`
- **THEN** that label is rendered on the corresponding connection in the diagram, with a directional arrowhead, on both the read-only detail page and the edit page's canvas

#### Scenario: A transition label's box grows to fit the label, up to a maximum size
- **WHEN** a step's transition `label` is longer than a short label like "yes" or "no" but still fits within the label box's maximum size
- **THEN** the box grows to wrap the label onto multiple lines and fit it in full, on both the read-only detail page and the edit page's canvas, instead of clamping text that would otherwise fit

#### Scenario: A transition label past the box's maximum size clamps with a tooltip
- **WHEN** a step's transition `label` is too long to fit even in the label box's maximum size
- **THEN** the rendered label clamps with an ellipsis at that maximum size, and hovering it shows the complete, untruncated label in a tooltip

#### Scenario: Clicking a connection's label opens its transition-edit modal
- **WHEN** a user clicks directly on a connection's label on the edit page's canvas
- **THEN** that connection's transition-edit modal opens, the same modal a click elsewhere on the connection's path already opens

#### Scenario: A connection's rendered path is never a stale, previously-computed route
- **WHEN** a Flow's `steps`, `autolayout_enabled`, `layout_direction`, or `layout_engine` changes, or an author drags a step, or the manual layout control is activated
- **THEN** every connection's rendered path is a direct curve freshly computed from its two endpoint steps' current positions at that moment — no connection retains a route computed before that change

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

### Requirement: Flow diagram layout direction and manual node positioning
A Flow SHALL carry a persisted `autolayout_enabled` boolean (default `true`), a persisted `layout_direction` (`LAYOUT_LEFT_RIGHT` or `LAYOUT_TOP_DOWN`; default `LAYOUT_LEFT_RIGHT`), and a persisted `layout_engine` (`dagre` or `elk`; default `dagre`) selecting which layout algorithm the automatic layout pass and the manual layout control use to compute positions. Each step MAY carry a `position` (`{x, y}`). Wherever the diagram is rendered — the read-only detail page or the edit page's canvas — a step SHALL render at its current `position`, with enough spacing between sibling nodes in the same layer that adjacent node borders do not touch. The automatic layout pass and the manual layout control SHALL NOT guarantee that a connection between two steps avoids visually crossing a third, unrelated step — layout spacing reduces how often this occurs but no rendered connection is checked or adjusted for it.

While `autolayout_enabled` is `true`: any change to a Flow's `steps` — adding, removing, or editing a step, including a drag — SHALL trigger the automatic layout pass to recompute every step's `position` using `layout_direction` and `layout_engine`, and the recomputed values SHALL be persisted. A step's `position` therefore always reflects the most recent automatic layout computation for the Flow's current `steps`, `layout_direction`, and `layout_engine`; no other value (e.g. a value set mid-drag, before the next recompute) persists across a subsequent `steps` change.

While `autolayout_enabled` is `false`: a step's `position` SHALL change only when an author drags it, when a new step is placed on being added (without invoking the automatic layout pass), or when the manual layout control described below is activated. No other `steps` change recomputes any step's `position`.

The edit page SHALL provide a manual-mode-only layout control that recomputes and overwrites every visible step's `position` once, using `layout_direction` and `layout_engine`, without changing `autolayout_enabled`. This control SHALL NOT be available while `autolayout_enabled` is `true`.

The edit page SHALL provide a control, alongside the `autolayout_enabled` toggle, to choose the Flow's `layout_engine`.

#### Scenario: While autolayout is on, every steps change recomputes and persists all positions
- **WHEN** `autolayout_enabled` is `true` and a Flow's `steps` are changed — a step is added, removed, or edited
- **THEN** every step's `position` is recomputed by the automatic layout pass using `layout_direction` and `layout_engine`, and persisted, and the diagram re-renders accordingly

#### Scenario: While autolayout is on, a drag has no lasting effect
- **WHEN** `autolayout_enabled` is `true` and an author drags a node to a new location on the edit page's canvas
- **THEN** the automatic layout pass recomputes every step's `position` (including the dragged one) again, and the dragged node does not remain at the manually-dropped location

#### Scenario: While autolayout is off, dragging a node persists exactly that position
- **WHEN** `autolayout_enabled` is `false` and an author drags a node to a new location on the edit page's canvas
- **THEN** that step's `position` is updated to the new coordinates, and no other step's `position` changes

#### Scenario: While autolayout is off, a newly added step is placed without invoking automatic layout
- **WHEN** `autolayout_enabled` is `false` and a new step is added to the Flow
- **THEN** the new step is given a `position` that does not overlap any existing step, without recomputing any other step's `position`

#### Scenario: The manual layout control recomputes every position, once, without enabling autolayout
- **WHEN** `autolayout_enabled` is `false` and an author activates the manual layout control
- **THEN** every visible step's `position` is recomputed according to `layout_direction` and `layout_engine`, and persisted, the canvas re-renders accordingly, and `autolayout_enabled` remains `false`

#### Scenario: The manual layout control is unavailable while autolayout is on
- **WHEN** `autolayout_enabled` is `true`
- **THEN** the edit page does not offer the manual layout control, since every `steps` change already keeps positions fully recomputed

#### Scenario: layout_direction is shared across viewers
- **WHEN** a Flow's `layout_direction` is `LAYOUT_TOP_DOWN` and two different users open its diagram
- **THEN** both render the diagram top-down, regardless of either user's own browser or session state

#### Scenario: layout_engine is shared across viewers
- **WHEN** a Flow's `layout_engine` is `elk` and two different users open its diagram
- **THEN** both compute positions using the ELK engine, regardless of either user's own browser or session state

#### Scenario: A Flow saved before layout_engine existed defaults to dagre
- **WHEN** a Flow created before this requirement's `layout_engine` field existed is read
- **THEN** its `layout_engine` is `dagre`

#### Scenario: Layout spacing does not guarantee crossing-free connections
- **WHEN** a Flow's shape causes one connection to visually cross a third, unrelated step under either `layout_engine`
- **THEN** the connection still renders as a direct curve between its two endpoints and the diagram does not adjust that connection or the crossed step's position to avoid it
