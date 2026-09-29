## MODIFIED Requirements

### Requirement: Visual Flow step authoring

The Flow create/edit page SHALL provide the interactive node canvas as its primary way to author its `steps` array. The canvas SHALL allow an author to add, edit, retype, connect, reposition, remove, and — for a transition between two existing steps — edit or delete that transition independently of either endpoint step, all without editing JSON directly. Adding a step SHALL open a node-type picker offering Actor, Component, Data, API, System, Team, API Call, Event, External, Step, Flow, and Link; selecting an entity-backed type or Flow SHALL show a searchable lookup scoped to that type (Actor/Team/Component/Data/API/System against the catalog, Flow against existing Flows), selecting API Call or Event SHALL show a searchable lookup across Endpoint/Operation records, and selecting Step, External, or Link SHALL show fields for its own data (title, optional summary, an optional color, an optional icon, and an optional free-text type label for Step; a label for External; an optional title, an optional summary, and a URL for Link). The API Call and Event tiles SHALL render disabled, with a tooltip explaining that the APIs plugin is required, when the running distribution does not have `atlas.apis` installed. Clicking an existing node SHALL reopen the same modal pre-filled with that step's current data, with a "Change type" action that resets type-specific fields. Connecting two nodes by dragging from one node's connection handle to another SHALL set the source step's `next_step` or append to its `next_steps`. An author SHALL additionally be able to open the same node-type picker directly from an existing node — via that node's own add control, or via a placeholder shown only next to a step with no outgoing transition — and once a type is chosen, the new step SHALL be connected as that node's `next_step` (or appended to its `next_steps` if it already has one) and positioned adjacent to it, without requiring a separate drag-to-connect gesture. Every node's add and remove controls on the canvas SHALL remain visible at all times, not only while the node is hovered. Clicking an existing transition SHALL open a modal to edit its `label` or delete the transition, without removing either step it connects. The canvas SHALL preserve the persisted Flow `steps` JSON grammar (field names `entity_ref`, `external_label`, `query_ref`, `event_ref`, `flow_ref`, `link_url` are unchanged by the node-type picker's renamed tile labels) and SHALL submit the same Flow API payload as the JSON editor.

#### Scenario: Add an entity-backed step from the node-type picker

- **WHEN** an author activates Add Step, selects the Component type, and chooses a Component from the catalog lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Component with that Component's actual subtype icon and color, and referencing the selected Component's canonical `component:name` ref

#### Scenario: Add an API Call step from the node-type picker

- **WHEN** an author activates Add Step, selects the API Call type, and chooses an Endpoint from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as an API Call showing that Endpoint's method on its chip, and storing that Endpoint's `query_ref` (its owning API, id, and snapshotted method/path)

#### Scenario: Add an Event step from the node-type picker

- **WHEN** an author activates Add Step, selects the Event type, and chooses an Operation from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as an Event showing that Operation's direction on its chip, and storing that Operation's `event_ref` (its owning API, id, and snapshotted direction/channel)

#### Scenario: Add a Flow step from the node-type picker

- **WHEN** an author activates Add Step, selects the Flow type, and chooses a Flow from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Flow node, and storing the selected Flow's id as `flow_ref`

#### Scenario: Add a Link step from the node-type picker

- **WHEN** an author activates Add Step, selects the Link type, enters a URL, and optionally a title and summary
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Link node, storing the entered URL as `link_url` and any entered title/summary

#### Scenario: API Call and Event tiles are disabled when atlas.apis is absent

- **WHEN** an author activates Add Step in a distribution that does not have `atlas.apis` installed
- **THEN** the API Call and Event tiles render disabled, with a tooltip explaining that the APIs plugin is required, and cannot be selected

#### Scenario: Add a plain Step node with a color, icon, and type label

- **WHEN** an author activates Add Step, selects the Step type, chooses a color, optionally picks an icon, and optionally enters a type label
- **THEN** a new node is added styled with the chosen color on its border and type chip, showing the chosen icon (or the default Step icon if none was picked), showing the entered type label on its chip (or "Step" if none was entered), and no `entity_ref`

#### Scenario: Add an External node

- **WHEN** an author activates Add Step, selects the External type, and enters a label
- **THEN** a new node is added styled as External, storing that label and no `entity_ref`, and the External tile's help text explains that this represents a step with no catalog record at all

#### Scenario: Retype an existing node

- **WHEN** an author clicks an existing Component node, activates "Change type", and selects Data, then chooses a Resource from the catalog lookup
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

### Requirement: Unified node visual styling

Every node kind on the canvas SHALL render with one consistent card anatomy: a neutral, theme-aware card fill; plain, uncolored title and subtitle text; a bold (2px) colored border carrying the kind's identity color; and a small colored chip showing the kind's icon and label. No node kind SHALL use a tinted or kind-colored card fill, and no node kind SHALL color its own title or subtitle text. The chip and title SHALL render at the same fixed vertical position within the card regardless of whether a subtitle is present — a card with no subtitle SHALL leave the resulting empty space below the title, and SHALL NOT re-center its chip and title as a block. Entity-backed kinds Actor, Team, Data, and System, External, Flow, and Link SHALL use a fixed color per kind and a fixed chip label naming the kind. Component and API SHALL use the color and icon of the referenced entity's actual subtype (Component: service/website/library/worker; API: openapi/grpc/asyncapi/graphql), falling back to a neutral default only when the reference does not resolve. API Call and Event SHALL use a color derived from the step's snapshotted HTTP method / direction respectively, and SHALL show that resolved method (e.g. "GET", "POST") or direction (title-cased "Send"/"Receive") as their chip label, falling back to the generic "API Call"/"Event" label only when the reference is unresolved. Step SHALL use the author's chosen per-instance color, applied consistently to both its border and its chip, and SHALL show the author's chosen type label on its chip, falling back to "Step" when no type label is set.

#### Scenario: Entity-backed node renders with neutral fill and colored border

- **WHEN** a Data node is rendered on the canvas
- **THEN** its card fill is the shared neutral background, its title and subtitle render in plain (uncolored) text, and its border and type chip render in Data's fixed color

#### Scenario: Component node shows its real subtype's icon and color

- **WHEN** a Component node referencing a `worker`-typed Component is rendered on the canvas
- **THEN** its border and type chip render in the color and icon associated with the `worker` Component type, not the color/icon of any other Component type

#### Scenario: API node shows its real subtype's icon and color

- **WHEN** an API node referencing a `grpc`-typed API is rendered on the canvas
- **THEN** its border and type chip render in the color and icon associated with the `grpc` API type, not a single generic API color/icon shared by every API type

#### Scenario: Step node's chosen color drives both its border and its chip

- **WHEN** a Step node with an author-chosen color is rendered on the canvas
- **THEN** its border and its type chip both render in that chosen color, and its card fill remains the shared neutral background

#### Scenario: Step node's chip shows a custom type label

- **WHEN** a Step node with an author-chosen type label of "Retry" is rendered on the canvas
- **THEN** its type chip shows "Retry" instead of "Step", and its title/subtitle/border/fill render unchanged

#### Scenario: Step node with no type label falls back to "Step"

- **WHEN** a Step node with no `type_label` set (or one that is blank/whitespace-only) is rendered on the canvas
- **THEN** its type chip shows "Step"

#### Scenario: API Call node's border and chip reflect its snapshotted method

- **WHEN** an API Call node with a snapshotted `POST` method is rendered on the canvas
- **THEN** its border and type chip render in the color associated with `POST`, its type chip shows the text "POST", and its card fill remains the shared neutral background

#### Scenario: Event node's border and chip reflect its snapshotted direction

- **WHEN** an Event node with a snapshotted `send` direction is rendered on the canvas
- **THEN** its border and type chip render in the color associated with `send`, and its type chip shows the text "Send"

#### Scenario: Flow and Link nodes use their own fixed color and chip label

- **WHEN** a Flow node and a Link node are both rendered on the canvas
- **THEN** each renders with its own fixed border/chip color, distinct from one another, and each chip shows a fixed label naming its kind ("Flow" or "Link") — as with the existing fixed-color kinds (e.g. Actor and Team already share one color), a fixed kind's color is not guaranteed unique across every other kind, only constant for that kind and compliant with the picker's own no-adjacent-color rule

#### Scenario: A card's chip and title hold position whether or not a subtitle is present

- **WHEN** a Step node with a summary and a Step node without a summary are both rendered on the canvas
- **THEN** both nodes' chip and title render at the same vertical offset from the top of their card, and only the node without a summary shows empty space below its title

### Requirement: Node-type picker tile colors and layout

The node-type picker's System tile SHALL use the same fixed identity color as System's canvas node, distinct from API's color. The node-type picker's Component tile color SHALL NOT be presented as representative of any specific Component subtype's actual canvas color, since a resolved Component's canvas color is always derived from its real subtype rather than a single generic color. The picker's grid arrangement SHALL NOT place two tiles carrying the same identity color adjacent to each other, horizontally or vertically. The picker's grid SHALL hold twelve tiles arranged as a two-column grid with no partial trailing row.

#### Scenario: System's picker tile and canvas node share one color, distinct from API

- **WHEN** the node-type picker is shown, and separately a System node is rendered on the canvas
- **THEN** both render in the same fixed color, and that color differs from API's fixed color

#### Scenario: No two adjacent picker tiles share a color

- **WHEN** the node-type picker's grid is rendered
- **THEN** for every pair of tiles that are horizontally or vertically adjacent, their identity colors differ

#### Scenario: The picker grid has no partial trailing row

- **WHEN** the node-type picker's grid is rendered with Flow and Link included alongside the ten existing tiles
- **THEN** the grid renders as six full rows of two tiles each, with no row containing only one tile

## ADDED Requirements

### Requirement: Flow reference lookup for Flow steps

The node-type picker and edit modal SHALL provide a searchable lookup for a step's `flow_ref`, searching by Flow name across existing Flows. The lookup SHALL store the selected Flow's id. An author SHALL be able to clear the reference, which reverts the node to the plain Step type. For a Flow-backed step, the modal SHALL NOT show editable Title or Summary fields — the node's card SHALL always render the referenced Flow's current `name` as its title and its current `description` as its subtitle, resolved live and never taken from any value stored on the step itself. A step carrying a non-empty `flow_ref` together with a non-empty `title` or `summary` SHALL be rejected on save. The lookup MAY include the Flow currently being edited among its results; selecting it is not an error.

#### Scenario: Select a Flow reference

- **WHEN** an author selects the Flow type and searches for and selects a Flow in its search lookup
- **THEN** the step stores that Flow's id as `flow_ref`, and the node renders styled as a Flow node

#### Scenario: Clear a Flow reference

- **WHEN** an author clears a step's Flow lookup
- **THEN** the step's `flow_ref` is removed, and the node reverts to the plain Step type

#### Scenario: Selecting a Flow does not offer Title/Summary fields to edit

- **WHEN** an author selects a reference for a Flow-backed step in the node-type picker or edit modal
- **THEN** no Title or Summary input is shown for that step; the modal offers no way to type custom text for it

#### Scenario: Flow-backed node renders the referenced Flow's live name and description

- **WHEN** a Flow-backed step's node is rendered, and the referenced Flow currently has `name: "Checkout"` and `description: "Cart to payment"`
- **THEN** the node's title reads "Checkout" and its subtitle reads "Cart to payment", regardless of any `title`/`summary` value stored on the step

### Requirement: Read-only navigate action for Flow and Link nodes

A Flow node's or Link node's card SHALL render a small navigate control, visually distinct from its identity chip, using an outbound-link icon. Activating it SHALL open the node's target — the referenced Flow's detail page for a Flow node, or the `link_url` for a Link node — in a new browser tab, leaving the current Flow's view unchanged. This control SHALL render only on the read-only detail page's canvas; the edit page's canvas SHALL NOT render it — clicking a Flow or Link node there opens its edit modal like any other node. Pressing down on a Flow or Link node's card and dragging, without activating the navigate control itself, SHALL pan the canvas as it would from any other node's card, and SHALL NOT trigger navigation. A Flow node whose `flow_ref` does not currently resolve to an existing Flow SHALL NOT render an active navigate control.

#### Scenario: Activating a Flow node's navigate control opens its target in a new tab

- **WHEN** a user activates a Flow node's navigate control on the read-only detail page
- **THEN** the referenced Flow's detail page opens in a new browser tab, and the current tab's view is unchanged

#### Scenario: Activating a Link node's navigate control opens its URL in a new tab

- **WHEN** a user activates a Link node's navigate control on the read-only detail page
- **THEN** the node's `link_url` opens in a new browser tab, and the current tab's view is unchanged

#### Scenario: The navigate control is absent on the edit page's canvas

- **WHEN** an author views a Flow or Link node on the edit page's canvas
- **THEN** no navigate control is rendered on its card

#### Scenario: Panning the canvas from a Flow or Link node does not navigate

- **WHEN** a user presses down on a Flow or Link node's card, away from the navigate control, and drags to pan the read-only canvas
- **THEN** the canvas viewport pans, and no navigation occurs

#### Scenario: A Flow node with an unresolved target has no active navigate control

- **WHEN** a Flow node's `flow_ref` does not currently resolve to an existing Flow
- **THEN** its navigate control is not rendered, or is rendered disabled

### Requirement: Stale Flow reference indicator

A Flow node whose `flow_ref` no longer resolves to an existing Flow SHALL show a warning icon on its card with a tooltip explaining that the referenced Flow no longer exists. This indicator SHALL be read-only: it SHALL NOT modify, clear, or remove the step's stored `flow_ref`, and SHALL NOT remove or alter the node itself. The same warning icon and tooltip SHALL also render for the step being edited inside the step-edit modal, not only on the canvas card.

#### Scenario: Flow node warns when its target no longer resolves

- **WHEN** a Flow node's `flow_ref` no longer resolves to an existing Flow (e.g. it was deleted)
- **THEN** the node shows a visible warning icon with a tooltip explaining the referenced Flow no longer exists

#### Scenario: Flow node with a resolving target shows no warning

- **WHEN** a Flow node's `flow_ref` resolves to an existing Flow
- **THEN** no warning icon is shown on that node

#### Scenario: The stale-reference indicator does not modify the stored flow_ref

- **WHEN** a Flow node's stale-reference warning icon is shown
- **THEN** the step's stored `flow_ref` remains unchanged, and the node itself is not removed from the canvas
