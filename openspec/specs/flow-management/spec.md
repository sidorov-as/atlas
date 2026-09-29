# flow-management Specification

## Purpose
Flows model a sequence of steps belonging to a home System, with catalog-validated entity references, an acyclic transition graph, filterable listing, and a UI for browsing and editing the step diagram.
## Requirements
### Requirement: Flow belongs to exactly one home System
A Flow SHALL have a required, non-nullable reference to exactly one `System` (its home system). A Flow's `name` SHALL be unique within its home system. `name` SHALL be stripped of leading/trailing whitespace and SHALL be rejected if the stripped value is empty or contains `/` or `:`; a PATCH that omits `name` SHALL leave the existing name unchanged, but a PATCH that explicitly provides an invalid `name` SHALL be rejected the same as on create. Deleting a System that is the home system of one or more Flows SHALL be blocked until those Flows are deleted or reassigned.

#### Scenario: Flow created with a home system
- **WHEN** a Flow is created with a valid home `system` reference, a unique `name` within that system, and a `steps` array
- **THEN** the Flow is persisted and appears under that system

#### Scenario: Flow requires a home system
- **WHEN** a Flow is created without a `system` reference
- **THEN** the request is rejected

#### Scenario: Duplicate name within the same system is rejected
- **WHEN** a Flow is created with a `name` that already exists on another Flow whose home system is the same
- **THEN** the request is rejected

#### Scenario: Deleting a system with flows is blocked
- **WHEN** an attempt is made to delete a System that is the home system of at least one Flow
- **THEN** the deletion is rejected until those Flows are deleted or reassigned to a different home system

#### Scenario: Empty or whitespace-only name is rejected
- **WHEN** a Flow is created or updated with `name` set to `""` or `"   "`
- **THEN** the request is rejected and no Flow is created or modified

#### Scenario: Name containing a forbidden character is rejected
- **WHEN** a Flow is created or updated with `name` containing `/` or `:`
- **THEN** the request is rejected

#### Scenario: Omitting name on a PATCH leaves it unchanged
- **WHEN** an existing Flow is updated via PATCH without a `name` field in the request body
- **THEN** the Flow's existing `name` is unchanged

### Requirement: Step entity references are validated against the catalog
Each step in a Flow's `steps` array MAY carry an `entity_ref` (a `kind:name` string using the catalog's existing ref grammar). On every save, every non-empty `entity_ref` SHALL be resolved against the catalog; a ref that does not resolve to an existing entity SHALL cause the save to be rejected. A step's `entity_ref` is a validated reference only — it is not stored as a foreign key and does not appear in the catalog's derived relations.

#### Scenario: Step with a resolvable entity_ref saves successfully
- **WHEN** a Flow is saved with a step whose `entity_ref` (e.g. `component:checkout-service`) resolves to an existing catalog entity
- **THEN** the Flow is persisted with that step's `entity_ref` intact

#### Scenario: Step with an unresolvable entity_ref is rejected
- **WHEN** a Flow is saved with a step whose `entity_ref` does not resolve to any existing catalog entity
- **THEN** the save is rejected and no Flow data is persisted or updated

#### Scenario: Step without an entity_ref is allowed
- **WHEN** a Flow is saved with a step that omits `entity_ref`
- **THEN** the save succeeds — a step is not required to reference a catalog entity

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

### Requirement: Flow list API supports filtering by system and team
The Flow list API SHALL support filtering results by home `system` and by the home system's owning team (Group).

#### Scenario: Filter flows by system
- **WHEN** the Flow list API is called with a `system` filter
- **THEN** only Flows whose home system matches are returned

#### Scenario: Filter flows by team
- **WHEN** the Flow list API is called with a `team` filter
- **THEN** only Flows whose home system's owner matches that team are returned

### Requirement: Flows are reachable from the catalog sidebar
The web UI SHALL expose a "Flows" item in the primary sidebar navigation, leading to a list page showing all Flows with search, a System filter, and a Team filter, and a "create Flow" action.

#### Scenario: Flows nav item is present
- **WHEN** a signed-in user views the sidebar
- **THEN** a "Flows" navigation item is present alongside Systems, Components, Resources, APIs, and Teams

#### Scenario: List page filters by system and team
- **WHEN** a user selects a System or a Team filter on the Flows list page
- **THEN** only Flows matching that filter are shown

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

### Requirement: Flow diagram nodes are typed and colored by kind
Each step's node SHALL render styled according to its kind: a step whose `entity_ref` targets a `user` or `group` SHALL render as an Actor or Team node respectively, `component` as a Service node, `resource` as a Data node, `api` as an API node, and `system` as a System node, each using a fixed color drawn from the catalog's existing C4 diagram palette, alongside an icon and a kind label visually distinguished from the node's own title text. A step with a `query_ref` SHALL render as a Query node using a magnifier icon, colored by its snapshotted HTTP `method` using the same color mapping Endpoints use for method badges. A step with an `event_ref` SHALL render as an Event node using a lightning-bolt icon, colored by its snapshotted `direction` using the same color mapping Operations use for direction badges. A step with a `flow_ref` SHALL render as a Flow node using the same icon as the "Flows" sidebar navigation item, in a fixed color distinct from every other kind's color. A step with a `link_url` SHALL render as a Link node using a chain-link icon, in a fixed color distinct from every other kind's color, including Flow's. A step with no `entity_ref`, `query_ref`, `event_ref`, `flow_ref`, or `link_url` SHALL render as a plain Step node (optionally colored per its `label_theme`) unless it carries `external_label`, in which case it SHALL render as an External node using the catalog's fixed External color. A node's title, subtitle, and kind label SHALL show their full value in a tooltip when hovered, regardless of whether the displayed text is visually truncated. This styling SHALL apply identically on the read-only detail page and the edit page's canvas.

#### Scenario: Component-backed step renders as a colored Service node
- **WHEN** a step's `entity_ref` resolves to a Component
- **THEN** the step's node renders with the Service node's fixed color, a Service icon, and a Service type label visually distinct from the node's title

#### Scenario: Query step renders with a method-colored magnifier icon
- **WHEN** a step carries a `query_ref` with a snapshotted `method` of `GET`
- **THEN** the step's node renders as a Query node with a magnifier icon and the color Endpoints use for a `GET` method badge

#### Scenario: Event step renders with a direction-colored bolt icon
- **WHEN** a step carries an `event_ref` with a snapshotted `direction` of `send`
- **THEN** the step's node renders as an Event node with a lightning-bolt icon and the color Operations use for a `send` direction badge

#### Scenario: Flow step renders with the Flows nav icon
- **WHEN** a step carries a `flow_ref`
- **THEN** the step's node renders as a Flow node using the same icon as the "Flows" sidebar navigation item, in its fixed color

#### Scenario: Link step renders with a chain-link icon
- **WHEN** a step carries a `link_url`
- **THEN** the step's node renders as a Link node using a chain-link icon, in its own fixed color, distinct from Flow's

#### Scenario: Step without an entity_ref, query_ref, event_ref, flow_ref, or link_url renders as a plain Step node
- **WHEN** a step has no `entity_ref`, `query_ref`, `event_ref`, `flow_ref`, `link_url`, or `external_label`
- **THEN** the step's node renders as a Step node, colored per its `label_theme` if set, or with a neutral default otherwise

#### Scenario: Step with an external_label renders as an External node
- **WHEN** a step has an `external_label` and no `entity_ref`
- **THEN** the step's node renders as an External node using the catalog's fixed External color

#### Scenario: Diagram styling matches between detail page and edit canvas
- **WHEN** the same Flow is viewed on its read-only detail page and on its edit page's canvas
- **THEN** corresponding steps render with identical node type, color, and icon on both

#### Scenario: Hovering truncated node text shows its full value
- **WHEN** a user hovers a node whose title or subtitle is too long to display in full
- **THEN** a tooltip shows the complete, untruncated text

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

### Requirement: Flow supports full Markdown documentation
A Flow SHALL persist an optional Markdown `documentation` field separately from its short `description`. The Flow create/edit form SHALL provide the Markdown Documentation editor after the system, short-description, and steps editing controls.

#### Scenario: Flow created without documentation
- **WHEN** a user creates a Flow without entering Documentation
- **THEN** the Flow is saved with an empty documentation value and its existing summary/steps behavior is unchanged

#### Scenario: Flow documentation is updated without changing steps
- **WHEN** a user edits only a Flow's Documentation and saves
- **THEN** the Flow's documentation changes while its system, name, short description, and steps remain unchanged

### Requirement: Flow create/edit form shares the standard entity-form header actions
The Flow create/edit form SHALL place its Save/Cancel actions in the same top header row (title left, actions right) used by System/Component/Resource/API Add/Edit forms and by the Flow detail page's own Edit/Delete actions, instead of a dedicated row under the title. The General/Flow tab structure and the General tab's side-by-side fields/Documentation layout SHALL remain unchanged.

#### Scenario: Flow form actions sit in the shared header row
- **WHEN** a user opens the create or edit form for a Flow
- **THEN** Save (or Create) and Cancel render in a header row above the General/Flow tabs, title on the left and the buttons on the right

#### Scenario: Flow tab actions are not duplicated in the Steps toolbar
- **WHEN** a user is on the Flow tab editing steps
- **THEN** Save and Cancel are not repeated next to the "Add Step" toolbar button — the header row above the tabs remains the only Save/Cancel control

### Requirement: Flow list preview panel and row actions
The Flows list page SHALL open a right-side preview panel when a row is clicked, showing a summary of that Flow with a link-through action to its full detail page, matching the preview-panel behavior of the Systems/Components/Resources/APIs/Teams list pages. A second, fast click on a row already open in the preview panel SHALL navigate to that Flow's detail page. Every row SHALL offer a context-actions control with exactly two entries: Edit and Remove, always shown (Flows cannot be YAML-managed).

#### Scenario: Clicking a Flow row opens the preview panel
- **WHEN** a user clicks a row on the Flows list page
- **THEN** a right-side panel opens showing that Flow's summary (its home System and step count), and the list remains visible

#### Scenario: A fast second click on the open Flow row navigates to its detail page
- **WHEN** a user clicks a Flow row, the preview panel opens for it, and the user clicks that same row again within the double-click window
- **THEN** they are navigated to that Flow's detail page

#### Scenario: Flow row always shows Edit and Remove
- **WHEN** a user views a row in the Flows list table
- **THEN** its context-actions control offers exactly two entries: Edit and Remove

### Requirement: Reading a Flow surfaces live status of entity_ref-targeted entities
When a Flow is read (list or detail), for each step carrying a non-empty `entity_ref` that resolves to any of the six entity-backed kinds (Actor, Team, System, Component, Resource, or API), the response SHALL additionally include that entity's current `title`, `description`, `status` (`active`/`removed`), and `deprecated` flag, resolved at read time — mirroring the existing live-status surfacing already provided for `query_ref`/`event_ref` steps in the `flow-query-event-steps` capability. `title`/`description` SHALL always be included whenever the reference resolves (rendering depends on them directly, not only as diagnostic information), independent of whether `status`/`deprecated` indicate anything noteworthy. This SHALL NOT modify the step's stored `entity_ref`, and SHALL NOT modify or derive from any `title`/`summary` stored on the step itself. When the referenced entity no longer resolves at all (e.g. it was purged), the read SHALL still succeed, presenting the step without a live status (including without `title`/`description`) rather than failing the Flow read.

#### Scenario: Reading a Flow reports a removed entity's current status
- **WHEN** a Flow containing a step whose `entity_ref` resolves to a Component with `status: removed` is read
- **THEN** the response includes that step's stored `entity_ref` unchanged, plus the Component's current `status: removed`

#### Scenario: Reading a Flow reports a deprecated entity's current status
- **WHEN** a Flow containing a step whose `entity_ref` resolves to a Component with `deprecated: true` is read
- **THEN** the response includes `deprecated: true` for that step's target

#### Scenario: A removed entity_ref target does not invalidate an existing Flow's reference
- **WHEN** an entity referenced by an existing Flow step's `entity_ref` becomes `removed` after the Flow was saved
- **THEN** the Flow continues to resolve and read successfully, showing the live `removed` status rather than rejecting the read

#### Scenario: Reading a Flow whose entity_ref target no longer resolves at all does not fail the read
- **WHEN** a Flow containing a step whose `entity_ref` no longer resolves to any entity (e.g. it was purged) is read
- **THEN** the read succeeds, the step's stored `entity_ref` is presented, and no live status — including no `title`/`description` — is included for that step

#### Scenario: Reading a Flow always includes an entity's live title and description
- **WHEN** a Flow containing a step whose `entity_ref` resolves to an active, non-deprecated System with `title: "Billing System"` and `description: "Owns invoicing"` is read
- **THEN** the response includes `title: "Billing System"` and `description: "Owns invoicing"` for that step, alongside its `status`/`deprecated`

#### Scenario: Live status is reported uniformly for all six entity-backed kinds
- **WHEN** a Flow containing steps whose `entity_ref` resolve one each to an Actor and a Team is read
- **THEN** the response includes live `title`/`description`/`status`/`deprecated` for both steps, the same as it would for a Component, Resource, API, or System

### Requirement: Flow diagram nodes visibly flag a removed or deprecated referenced entity
A step's node whose resolved reference (`entity_ref`, `query_ref`, or `event_ref`) currently carries `status: removed` or `deprecated: true` SHALL render a visible warning indicator on the node, distinguishing removed from deprecated, on both the read-only detail page and the edit page's canvas. An Event node whose stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address` SHALL additionally render this warning indicator, distinguished from the removed/deprecated indicators, even when the Operation itself is `active` and not deprecated.

#### Scenario: A step referencing a removed entity shows a warning indicator
- **WHEN** a Flow's diagram renders a step whose `entity_ref` resolves to a `removed` Component
- **THEN** that step's node shows a visible removed-status warning indicator

#### Scenario: A step referencing a deprecated entity shows a distinct warning indicator
- **WHEN** a Flow's diagram renders a step whose `entity_ref` resolves to a `deprecated` (but active) Resource
- **THEN** that step's node shows a visible deprecated-status warning indicator, visually distinguished from the removed-status indicator

#### Scenario: A step referencing an active, non-deprecated entity shows no warning
- **WHEN** a Flow's diagram renders a step whose reference resolves to an entity that is `active` and not `deprecated`
- **THEN** no warning indicator is shown on that node

#### Scenario: An Event node whose direction/channel has drifted shows a warning indicator
- **WHEN** a Flow's diagram renders an Event step whose stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address`, and that Operation is `active` and not deprecated
- **THEN** the node shows a visible warning indicator for the drift, even though neither removed nor deprecated is true

### Requirement: Write affordances are hidden for a read-only session
`FlowDetailPage`'s Edit and Delete actions, the Flows list Add action, and its per-row write actions (both outside `EntityDetailShell`/`EntityListPage`, so not covered by `catalog-web-ui`'s equivalent requirement) SHALL be hidden for a read-only session, and the Flow create/edit form route SHALL redirect a read-only session away, the same way `catalog-web-ui`'s write-affordance requirement gates the core-shell-backed entity kinds.

#### Scenario: Read-only session sees no Edit/Delete on a Flow detail page
- **WHEN** a read-only session opens a Flow's detail page
- **THEN** neither the Edit nor the Delete action is shown

#### Scenario: Read-only session sees no row actions on the Flows list
- **WHEN** a read-only session views a row on the Flows list table
- **THEN** no write action is shown for that row while permitted read/navigation actions remain

#### Scenario: Read-only session is redirected away from a Flow create or edit URL
- **WHEN** a read-only session navigates directly to `/flows/new` or `/flows/:id/edit`
- **THEN** they are redirected away without seeing the form

#### Scenario: Non-read-only session is unaffected
- **WHEN** an authenticated session that is not flagged read-only opens a Flow detail page or the Flows list
- **THEN** Edit/Delete and row actions render exactly as they do today

#### Scenario: Read-only session sees no Flow Add action
- **WHEN** a read-only session opens the Flows list
- **THEN** the Add action is absent

#### Scenario: Flow mutation bypasses the UI
- **WHEN** a read-only Principal invokes a Flow mutation directly
- **THEN** the backend returns 403 before persistence or other mutation side effects

### Requirement: Read-only Flow diagram provides an Export control
A Flow's read-only detail page diagram SHALL provide an Export control offering an SVG/PNG format choice, a "Transparent background" checkbox, and a "Grid" checkbox, each defaulted to SVG format, transparent checked, and grid checked on every open, with none of the three persisting between exports or page loads. Activating Export SHALL download the diagram as it is currently laid out, honoring the selected format, background, and grid options, without altering the visible canvas at any point before, during, or after the export. This control SHALL render only on the read-only detail page's diagram; the edit page's canvas SHALL NOT render it.

#### Scenario: Opening the Export control shows default options
- **WHEN** a user activates the Export control on a Flow's read-only detail page
- **THEN** a popup opens offering an SVG/PNG format choice defaulted to SVG, a "Transparent background" checkbox defaulted to checked, and a "Grid" checkbox defaulted to checked

#### Scenario: Exporting the diagram with default options
- **WHEN** a user opens the Export control and activates the Export action without changing any option
- **THEN** the system downloads the current Flow diagram as an SVG file with a transparent background and the grid included

#### Scenario: Exporting with a white background and no grid
- **WHEN** a user unchecks "Transparent background" and unchecks "Grid" before activating Export
- **THEN** the downloaded file has a white background and omits the grid dots, in either SVG or PNG format

#### Scenario: Export options do not affect the live viewer
- **WHEN** a user unchecks "Grid" or "Transparent background" in the Export popup, with or without completing an export
- **THEN** the read-only detail page's on-screen canvas continues to show its grid and background unchanged throughout

#### Scenario: Export options reset on next open
- **WHEN** a user changes the format, transparency, or grid option, exports or closes the popup, and later reopens the Export control
- **THEN** the popup shows the default format (SVG), transparent background checked, and grid checked, regardless of the previous export's choices

#### Scenario: No Export control on the edit page canvas
- **WHEN** a user opens a Flow's edit page
- **THEN** its canvas shows no Export control

### Requirement: Flow content fields are size-bounded
A Flow's `description` and `documentation` SHALL each be bounded to a fixed maximum length, and its `steps` list SHALL be bounded to a fixed maximum number of entries.

#### Scenario: Oversized description or documentation is rejected
- **WHEN** a Flow is created or updated with `description` or `documentation` longer than its declared maximum length
- **THEN** the request is rejected with a validation error and no Flow is created or modified

#### Scenario: Too many steps is rejected
- **WHEN** a Flow is created or updated with more `steps` entries than the declared maximum
- **THEN** the request is rejected with a validation error and no Flow is created or modified
